// irelandfootball Worker: serves ./site and proxies a small set of API-Football endpoints under /api/* for the Ireland hub.
// Forked from the manutd.wiki Worker (SITE1); the cache design is the same:
//  - Every upstream answer is stored in KV for TTL seconds and kept 7 days beyond that. A stale copy is served at once while
//    one background refresh runs, so a visitor never waits on the API and never sees its errors.
//  - A cron warms the core endpoints hourly. Error answers are never cached.
// The key lives in the API_FOOTBALL_KEY secret. Never put it in the repo or in chat.

const TEAM = 776;         // Republic of Ireland in API-Football
const API = "https://v3.football.api-sports.io";
const KEEP = 7 * 24 * 3600;     // seconds a copy stays in KV after it goes stale

// National-team competitions are labelled by the year they start and friendlies by calendar year, so the current list needs
// this year's label and last year's (a Nations League that began last autumn, say).
function seasons(now = new Date()) { const y = now.getUTCFullYear(); return [y - 1, y]; }

// name -> { path(url) or paths(url), ttl seconds }
const ROUTES = {
  "/api/status":   { ttl: 300,   path: () => `/status` },
  "/api/fixtures": { ttl: 1800,  paths: () => seasons().map((s) => `/fixtures?team=${TEAM}&season=${s}`) },
  "/api/standings": { ttl: 1800, custom: standings },
  "/api/team-season": { ttl: 30 * 86400, path: (u) => `/fixtures?team=${TEAM}&season=${num(u, "season")}` },   // past years, for the archive builders
  "/api/squad":    { ttl: 21600, path: () => `/players/squads?team=${TEAM}` },
  "/api/match":    { ttl: 21600, live: true, path: (u) => `/fixtures?id=${num(u, "fixture")}` },
  "/api/player":   { ttl: 86400, path: (u) => `/players?id=${num(u, "id")}&season=${seasons()[1]}` },
};
function num(u, k) { return String(parseInt(u.searchParams.get(k) || "0", 10) || 0); }

// Warmed every hour by the cron so pages never wait on the API.
const WARM = ["/api/fixtures", "/api/standings", "/api/squad"];

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (url.hostname.startsWith("www.")) return Response.redirect(url.origin.replace("//www.", "//") + url.pathname + url.search, 301);
    // dev Worker (env.dev in wrangler.jsonc): data, alerts, collections, calendars and portraits come from the live site
    if (env.UPSTREAM && /^\/(api\/|wiki$|wiki-raw$|push\/|collection$|calendar\.ics$|img\/)/.test(url.pathname)) return fetch(new Request(env.UPSTREAM + url.pathname + url.search, request));
    if (url.pathname.startsWith("/img/player/")) return portrait(url, ctx);
    if (url.pathname === "/wiki") return wiki(url, env, ctx);
    if (url.pathname === "/wiki-raw") return wikiRaw(url, env, ctx);
    if (url.pathname === "/collection") { try { return await collection(request, url, env); } catch (e) { return json({ error: "collection: " + (e && e.message || e) }, 500); } }
    if (url.pathname === "/calendar.ics") { try { return await calendar(url, env); } catch (e) { return json({ error: "calendar: " + (e && e.message || e) }, 500); } }
    if (url.pathname.startsWith("/push/")) { try { return await push(request, url, env, ctx); } catch (e) { return json({ error: "push: " + (e && e.message || e) }, 500); } }
    // dev site: its own icons (crest with an orange DEV band), so its tab and home-screen icon can't be mistaken for the live site
    if (env.UPSTREAM && /^\/assets\/(favicon-32|apple-touch-icon|icon-192|icon-512|icon-512-maskable)\.png$/.test(url.pathname)) { const u = new URL(request.url); u.pathname = "/assets/dev/" + url.pathname.split("/").pop(); return env.ASSETS.fetch(new Request(u, request)); }
    if (!url.pathname.startsWith("/api/")) return page(request, env);

    if (url.pathname === "/api/form") {
      const body = (await env.MU_CACHE.get(FORM_KEY)) || '{"players":{}}';
      if (env.API_FOOTBALL_KEY) ctx.waitUntil(formStep(env).catch((e) => console.log("form", e && e.message)));
      return new Response(body, { headers: headers("kv-form") });
    }
    const route = ROUTES[url.pathname];
    if (!route) return json({ error: "unknown route" }, 404);
    if (!env.API_FOOTBALL_KEY) return json({ error: "API_FOOTBALL_KEY secret not set on the Worker" }, 500);

    const key = "api:v2:" + url.pathname + url.search;
    const { body, fresh, age } = await load(env, key);
    if (route.live && body) {
      // Live window: from 90 minutes before kick-off until the match is finished, anything older than 60s is stale.
      try { const j = JSON.parse(body), f = j.response && j.response[0]; if (f) { const ko = f.fixture.timestamp * 1000, st = f.fixture.status.short, now = Date.now();
        const inWindow = (now > ko - 90 * 60000 && !/FT|AET|PEN|CANC|PST|ABD|AWD|WO/.test(st)) || /1H|HT|2H|ET|BT|P|LIVE|INT|SUSP/.test(st);
        const ours = f.teams.home.id === TEAM || f.teams.away.id === TEAM, staleAfter = ours ? 60 : 900;
        if (inWindow && age > staleAfter) { ctx.waitUntil(refresh(env, key, route, url)); return answer(body, "kv-live-stale", age); } if (inWindow) return answer(body, "kv-live", age); } } catch (e) {}
    }
    if (body && fresh) return answer(body, "kv-hit", age);
    if (body) { ctx.waitUntil(refresh(env, key, route, url)); return answer(body, "kv-stale", age); }

    // Nothing cached yet: fetch now (the first visitor pays once; the cron keeps it warm after that).
    const r = await refresh(env, key, route, url);
    return r.ok ? answer(r.body, "upstream", 0) : new Response(r.body, { status: 200, headers: headers("upstream-error") });
  },

  // Hourly warm-up. Sequential and spaced, so it never trips the per-minute cap.
  async scheduled(event, env, ctx) {
    if (event.cron === "* * * * *") { ctx.waitUntil(pushTick(env).catch((e) => console.log("pushTick", e && e.message))); return; }
    ctx.waitUntil(formStep(env).catch((e) => console.log("form", e && e.message)));
    ctx.waitUntil((async () => {
      for (const p of WARM) {
        const url = new URL("https://site.local" + p + "?v=4");
        const route = ROUTES[url.pathname], key = "api:v2:" + url.pathname + url.search;
        const { body, age } = await load(env, key);
        if (body && age < route.ttl * 0.8) continue;
        await refresh(env, key, route, url);
        await sleep(1200);
      }
    })());
  },
};

// ---- Club form: each squad player's club season and latest club game ---------------------------------------------------
// A player costs 3 API calls. A step does at most FORM_STEP players, so it stays well inside a Worker's subrequest limit, and it
// only touches players whose entry is older than FORM_AGE. The cron and page visits each trigger a step, guarded by a short lock.
const FORM_KEY = "form:v1", FORM_STEP = 8, FORM_AGE = 12 * 3600 * 1000;
function clubSeason(now = new Date()) { return now.getUTCMonth() >= 6 ? now.getUTCFullYear() : now.getUTCFullYear() - 1; }   // 2026/27 is labelled 2026
async function formPlayer(env, id) {
  const a = await fetchOne(env, `/players?id=${id}&season=${clubSeason()}`);
  if (!a.clean) return null;
  const rows = ((a.j.response || [])[0] || {}).statistics || [], clubs = rows.filter((s) => s.team && s.team.id !== TEAM && s.league && s.league.country !== "World");
  if (!clubs.length) return { at: Date.now(), none: 1 };
  const apps = (s) => (s.games && s.games.appearences) || 0;
  const byTeam = {}; clubs.forEach((s) => { const t = byTeam[s.team.id] = byTeam[s.team.id] || { id: s.team.id, name: s.team.name, logo: s.team.logo, apps: 0, min: 0, goals: 0, assists: 0, saves: 0, conceded: 0 }; t.apps += apps(s); t.min += (s.games && s.games.minutes) || 0; t.goals += (s.goals && s.goals.total) || 0; t.assists += (s.goals && s.goals.assists) || 0; t.saves += (s.goals && s.goals.saves) || 0; t.conceded += (s.goals && s.goals.conceded) || 0; });
  const club = Object.values(byTeam).sort((x, y) => y.apps - x.apps)[0];
  const out = { at: Date.now(), club };
  const b = await fetchOne(env, `/fixtures?team=${club.id}&last=1`), f = b.clean && (b.j.response || [])[0];
  if (f) {
    const home = f.teams.home.id === club.id, last = { id: f.fixture.id, d: f.fixture.date, opp: (home ? f.teams.away : f.teams.home).name, gf: home ? f.goals.home : f.goals.away, ga: home ? f.goals.away : f.goals.home, league: f.league.name };
    const c = await fetchOne(env, `/fixtures/players?fixture=${f.fixture.id}&team=${club.id}`), me = c.clean && (((c.j.response || [])[0] || {}).players || []).find((p) => p.player.id === Number(id));
    if (me) { const s = (me.statistics || [])[0] || {}; last.min = (s.games && s.games.minutes) || 0; last.goals = (s.goals && s.goals.total) || 0; last.assists = (s.goals && s.goals.assists) || 0; last.rating = s.games && s.games.rating; last.sub = !!(s.games && s.games.substitute); last.inSquad = 1; }
    out.last = last;
  }
  return out;
}
async function formStep(env) {
  if (await env.MU_CACHE.get("form:lock")) return;
  let sq = await load(env, "api:v2:/api/squad?v=4");
  if (!sq.body) { const r = await refresh(env, "api:v2:/api/squad?v=4", ROUTES["/api/squad"], new URL("https://site.local/api/squad?v=4")); if (!r.ok) return; sq = { body: r.body }; }
  const squad = ((JSON.parse(sq.body).response || [])[0] || {}).players || [], state = JSON.parse((await env.MU_CACHE.get(FORM_KEY)) || '{"players":{}}');
  const now = Date.now(), due = squad.filter((p) => !state.players[p.id] || now - state.players[p.id].at > FORM_AGE).slice(0, FORM_STEP);
  if (!due.length) return;
  await env.MU_CACHE.put("form:lock", "1", { expirationTtl: 120 });
  // In parallel: work after a response only gets about 30 seconds, and 24 calls in a row can take longer than that.
  const got = await Promise.all(due.map((p) => formPlayer(env, p.id).catch(() => null)));
  got.forEach((x, i) => { if (x) state.players[due[i].id] = x; });
  const keep = new Set(squad.map((p) => String(p.id))); Object.keys(state.players).forEach((k) => { if (!keep.has(k)) delete state.players[k]; });
  state.updated = now;
  await env.MU_CACHE.put(FORM_KEY, JSON.stringify(state));
}

// ---- Match alerts: Web Push (subscriptions in KV under push:sub:<sha256(endpoint)>, VAPID keys generated into KV) ----------
const b64u = { enc: (b) => btoa(String.fromCharCode(...new Uint8Array(b))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, ""), dec: (s) => { s = s.replace(/-/g, "+").replace(/_/g, "/"); while (s.length % 4) s += "="; return Uint8Array.from(atob(s), (c) => c.charCodeAt(0)); } };
const cat = (...as) => { const n = as.reduce((t, a) => t + a.length, 0), out = new Uint8Array(n); let o = 0; for (const a of as) { out.set(a, o); o += a.length; } return out; };
const te = (s) => new TextEncoder().encode(s);
async function vapidKeys(env) {
  let j = await env.MU_CACHE.get("push:vapid", "json"); if (j) return j;
  const kp = await crypto.subtle.generateKey({ name: "ECDSA", namedCurve: "P-256" }, true, ["sign", "verify"]);
  j = { pub: b64u.enc(await crypto.subtle.exportKey("raw", kp.publicKey)), priv: await crypto.subtle.exportKey("jwk", kp.privateKey) };
  await env.MU_CACHE.put("push:vapid", JSON.stringify(j)); return j;
}
async function vapidHeader(env, endpoint) {
  const k = await vapidKeys(env), aud = new URL(endpoint).origin;
  const hdr = b64u.enc(te(JSON.stringify({ typ: "JWT", alg: "ES256" }))), body = b64u.enc(te(JSON.stringify({ aud, exp: Math.floor(Date.now() / 1000) + 12 * 3600, sub: "mailto:richardmcallister@gmail.com" })));
  const key = await crypto.subtle.importKey("jwk", k.priv, { name: "ECDSA", namedCurve: "P-256" }, false, ["sign"]);
  const sig = await crypto.subtle.sign({ name: "ECDSA", hash: "SHA-256" }, key, te(hdr + "." + body));
  return `vapid t=${hdr}.${body}.${b64u.enc(sig)}, k=${k.pub}`;
}
async function hkdf(salt, ikm, info, len) { const k = await crypto.subtle.importKey("raw", ikm, "HKDF", false, ["deriveBits"]); return new Uint8Array(await crypto.subtle.deriveBits({ name: "HKDF", hash: "SHA-256", salt, info }, k, len * 8)); }
async function encryptPayload(sub, payload) {
  const ua = b64u.dec(sub.keys.p256dh), auth = b64u.dec(sub.keys.auth);
  const local = await crypto.subtle.generateKey({ name: "ECDH", namedCurve: "P-256" }, true, ["deriveBits"]);
  const localPub = new Uint8Array(await crypto.subtle.exportKey("raw", local.publicKey));
  const uaKey = await crypto.subtle.importKey("raw", ua, { name: "ECDH", namedCurve: "P-256" }, false, []);
  const shared = new Uint8Array(await crypto.subtle.deriveBits({ name: "ECDH", public: uaKey }, local.privateKey, 256));
  const salt = crypto.getRandomValues(new Uint8Array(16));
  const ikm = await hkdf(auth, shared, cat(te("WebPush: info\0"), ua, localPub), 32);
  const cek = await hkdf(salt, ikm, te("Content-Encoding: aes128gcm\0"), 16), nonce = await hkdf(salt, ikm, te("Content-Encoding: nonce\0"), 12);
  const key = await crypto.subtle.importKey("raw", cek, "AES-GCM", false, ["encrypt"]);
  const ct = new Uint8Array(await crypto.subtle.encrypt({ name: "AES-GCM", iv: nonce }, key, cat(te(payload), new Uint8Array([2]))));
  return cat(salt, new Uint8Array([0, 0, 16, 0]), new Uint8Array([65]), localPub, ct);   // header: salt | rs=4096 | idlen=65 | local public key
}
async function sendPush(env, rec, msg) {
  const sub = rec.sub, body = await encryptPayload(sub, JSON.stringify(msg).replace(/&apos;/g, "'"));
  const r = await fetch(sub.endpoint, { method: "POST", headers: { "content-encoding": "aes128gcm", "content-type": "application/octet-stream", "ttl": String(msg.ttl || 3600), "urgency": "high", "authorization": await vapidHeader(env, sub.endpoint) }, body });
  if (r.status === 404 || r.status === 410) { await env.MU_CACHE.delete(rec.key); return "gone"; }
  return r.status;
}
async function subKey(endpoint) { const h = await crypto.subtle.digest("SHA-256", te(endpoint)); return "push:sub:" + [...new Uint8Array(h)].map((b) => b.toString(16).padStart(2, "0")).join(""); }
async function allSubs(env) {
  const out = []; let cursor;
  do { const l = await env.MU_CACHE.list({ prefix: "push:sub:", cursor }); for (const k of l.keys) { const v = await env.MU_CACHE.get(k.name, "json"); if (v && v.sub) out.push({ key: k.name, ...v }); } cursor = l.list_complete ? null : l.cursor; } while (cursor);
  return out;
}
async function push(request, url, env, ctx) {
  const p = url.pathname;
  if (p === "/push/key") return json({ key: (await vapidKeys(env)).pub });
  if (request.method !== "POST") return json({ error: "POST" }, 405);
  const b = await request.json().catch(() => ({}));
  if (p === "/push/subscribe") {
    if (!b.sub || !b.sub.endpoint || !b.sub.keys) return json({ error: "subscription required" }, 400);
    const prefs = Object.assign({ goals: true, lineups: true, kickoff: true, result: true, milestones: true }, b.prefs || {});
    const key = await subKey(b.sub.endpoint), old = await env.MU_CACHE.get(key, "json");
    await env.MU_CACHE.put(key, JSON.stringify({ sub: b.sub, prefs, created: old ? old.created : Date.now(), seen: Date.now(), ua: (request.headers.get("user-agent") || "").slice(0, 120) }));
    return json({ ok: true, prefs });
  }
  if (p === "/push/unsubscribe") { if (b.endpoint) await env.MU_CACHE.delete(await subKey(b.endpoint)); return json({ ok: true }); }
  if (p === "/push/test") {
    if (!b.endpoint) return json({ error: "endpoint required" }, 400);
    const rec = await env.MU_CACHE.get(await subKey(b.endpoint), "json"); if (!rec) return json({ error: "not subscribed" }, 404);
    const st = await sendPush(env, { key: await subKey(b.endpoint), ...rec }, { title: "Match alerts are on", body: "You'll hear about team news, goals and the final score for Ireland. This is a test.", url: "/", tag: "test" });
    return json({ ok: st === 201 || st === 200, status: st });
  }
  return json({ error: "unknown" }, 404);
}

// A minute cron watches the next fixture from an hour before kick-off to the final whistle. Goal events are reconciled against the
// official score, so a goal VAR rules out is never announced.
async function pushTick(env) {
  const now = Date.now(); let fx = await load(env, "api:v2:/api/fixtures?v=4");
  if (!fx.body) { const r = await refresh(env, "api:v2:/api/fixtures?v=4", ROUTES["/api/fixtures"], new URL("https://site.local/api/fixtures?v=4")); if (!r.ok) return; fx = { body: r.body }; }
  const list = JSON.parse(fx.body).response || [], next = list.filter((m) => !/FT|AET|PEN|CANC|PST|ABD|AWD|WO/.test(m.fixture.status.short)).sort((a, b) => a.fixture.timestamp - b.fixture.timestamp)[0];
  if (!next) return;
  const ko = next.fixture.timestamp * 1000, id = next.fixture.id;
  if (now < ko - 65 * 60000 || now > ko + 3.5 * 3600000) return;
  const subs = await allSubs(env); if (!subs.length) return;
  const sk = "push:state:" + id, state = (await env.MU_CACHE.get(sk, "json")) || { sent: {} };
  const home = next.teams.home.id === TEAM, opp = (home ? next.teams.away : next.teams.home).name, name = (h, a) => home ? "Ireland " + h + "–" + a + " " + opp : opp + " " + h + "–" + a + " Ireland";
  const out = []; const fan = (pref, msg) => out.push({ pref, msg: Object.assign({ url: "/match/?id=" + id, tag: "m" + id, ko: next.fixture.date, opp, home, comp: next.league.name }, msg) });
  if (state.sent.ft) return;   // the game is over: no more feed calls for it
  // kick-off reminder, an hour before
  if (!state.sent.kickoff && now >= ko - 62 * 60000 && now < ko - 45 * 60000) { state.sent.kickoff = 1; fan("kickoff", { title: (home ? "Ireland v " + opp : opp + " v Ireland") + " in an hour", body: next.league.name + " · " + (next.fixture.venue && next.fixture.venue.name || ""), kind: "kickoff" }); }
  // live detail: one feed call a minute, shared with the match page's cache
  const key = "api:v2:/api/match?fixture=" + id + "&v=4", route = ROUTES["/api/match"]; let m = await load(env, key);
  if (!m.body || m.age > 50) { const r = await refresh(env, key, route, new URL("https://site.local/api/match?fixture=" + id + "&v=4")); if (r.ok) m = { body: r.body }; }
  const f = m.body ? (JSON.parse(m.body).response || [])[0] : null;
  if (f) {
    const st = f.fixture.status.short, g = f.goals;
    if (!state.sent.lineups && (f.lineups || []).length === 2) {
      state.sent.lineups = 1; const us = f.lineups.find((l) => l.team.id === TEAM);
      if (us) fan("lineups", { title: "Team news: Ireland XI", body: (us.formation ? us.formation + " · " : "") + us.startXI.map((x) => x.player.name.split(" ").pop()).join(", "), kind: "lineups" });
    }
    // Goal events reconciled against the official score: the feed logs a goal as soon as the ball goes in; if VAR rules it
    // out the event can stay (usually with no scorer) while f.goals never moves. Only goals the score counts are sent,
    // so a goal is announced on the first tick the score corroborates it, and a disallowed one never is.
    const GE = (f.events || []).filter((e) => e.type === "Goal" && e.detail !== "Missed Penalty" && e.time && e.time.elapsed != null);
    for (const [t, allowed] of [[f.teams.home, g.home], [f.teams.away, g.away]]) {
      const mine = GE.filter((e) => e.team.id === t.id); mine.forEach((e) => { e.ok = true; });
      const extra = mine.length - (allowed == null ? mine.length : allowed);
      if (extra > 0) mine.filter((e) => !(e.player && e.player.name)).concat(mine.filter((e) => e.player && e.player.name).reverse()).slice(0, extra).forEach((e) => { e.ok = false; });
    }
    for (const e of GE) {
      if (!e.ok) continue;
      const eid = "g" + e.team.id + "-" + (e.player && e.player.id) + "-" + e.time.elapsed + "+" + (e.time.extra || 0);
      if (state.sent[eid]) continue; state.sent[eid] = 1;
      const us = e.team.id === TEAM, minute = e.time.elapsed + (e.time.extra ? "+" + e.time.extra : "") + "'";
      // running score after this goal, counted from the events so far
      const sofar = GE.filter((x) => x.ok && (x.time.elapsed < e.time.elapsed || (x.time.elapsed === e.time.elapsed && (x.time.extra || 0) <= (e.time.extra || 0)))), hg = sofar.filter((x) => x.team.id === f.teams.home.id).length, ag = sofar.length - hg;
      fan("goals", { title: (us ? "GOAL! " : "") + name(hg, ag), body: (e.player && e.player.name || "") + " " + minute + (e.detail === "Penalty" ? " (pen)" : e.detail === "Own Goal" ? " (og)" : "") + (e.assist && e.assist.name ? " · assist " + e.assist.name : ""), kind: us ? "goal" : "goal-against" });
    }
    if (!state.sent.ht && st === "HT") { state.sent.ht = 1; fan("result", { title: "Half-time: " + name(g.home, g.away), body: next.league.name, kind: "ht" }); }
    if (!state.sent.ft && /FT|AET|PEN/.test(st)) { state.sent.ft = 1; const pen = st === "PEN" && f.score && f.score.penalty ? " · " + f.score.penalty.home + "–" + f.score.penalty.away + " on penalties" : ""; const w = g.home === g.away ? (st === "PEN" ? "" : "Draw") : ((g.home > g.away) === home ? "Ireland win" : "Ireland lose"); fan("result", { title: "Full-time: " + name(g.home, g.away) + (st === "AET" ? " (aet)" : ""), body: (w ? w + pen + " · " : "") + next.league.name, kind: "ft", ttl: 86400 }); }
    if (state.sent.ft && !state.sent.ms) { state.sent.ms = 1; try { for (const x of await milestones(env, f)) fan("milestones", { title: "Milestone: " + x.name, body: x.what.join(" · ") + " · v " + opp, kind: "milestone", url: "/milestones/", ttl: 86400 }); } catch (e) { console.log("milestones", e && e.message); } }
  }
  await env.MU_CACHE.put(sk, JSON.stringify(state), { expirationTtl: 2 * 86400 });
  for (const o of out) for (const s of subs) { if (s.prefs && s.prefs[o.pref] === false) continue; try { await sendPush(env, s, o.msg); } catch (e) { console.log("push fail", e && e.message); } }
}



// Runs before the page paints: picks the language (?lang=, then the saved choice) and keeps Irish pages hidden until translated. See site/i18n.js.
const LANG_HEAD = '<script>(function(){var l=null;try{l=new URLSearchParams(location.search).get("lang");if(l==="ga"||l==="en")localStorage.setItem("mu:lang",l);else l=localStorage.getItem("mu:lang")}catch(e){}window.MU_LANG=l==="ga"?"ga":"en";if(l==="ga"){var d=document.documentElement;d.lang="ga";d.classList.add("i18n-wait");setTimeout(function(){d.classList.remove("i18n-wait")},3000)}})()</script><style>html.i18n-wait body{visibility:hidden}</style><script src="/i18n.js"></script>';

// ---- Shirt collection: owned / wishlist / notes, stored in KV under a hash of the owner's passphrase.
// GET  /collection?key=…         → the saved collection (or an empty one)
// PUT  /collection?key=…  body   → replace it (JSON, 64 KB max)
async function collection(request, url, env) {
  const key = (url.searchParams.get("key") || "").trim();
  if (key.length < 6) return json({ error: "a collection key of at least 6 characters is required" }, 400);
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode("ie-collection:" + key));
  const id = "col:v1:" + Array.from(new Uint8Array(buf)).map((b) => b.toString(16).padStart(2, "0")).join("");
  const hd = { "cache-control": "no-store", "content-type": "application/json; charset=utf-8" };
  if (request.method === "PUT") {
    const body = await request.text();
    if (body.length > 65536) return new Response(JSON.stringify({ error: "too large" }), { status: 413, headers: hd });
    try { const j = JSON.parse(body); if (!j || typeof j !== "object" || !Array.isArray(j.owned) || !Array.isArray(j.wish)) throw 0; } catch (e) { return new Response(JSON.stringify({ error: "expected {owned:[],wish:[],notes:{}}" }), { status: 400, headers: hd }); }
    await env.MU_CACHE.put(id, body);
    return new Response(JSON.stringify({ ok: true, saved: new Date().toISOString() }), { headers: hd });
  }
  if (request.method !== "GET") return json({ error: "method not allowed" }, 405);
  const cur = await env.MU_CACHE.get(id);
  return new Response(cur || JSON.stringify({ owned: [], wish: [], notes: {}, updated: null }), { headers: hd });
}

// ---- Fixture calendar: every game in the fixtures feed, one event per fixture id, so a subscribed calendar follows a moved kick-off
function icsEsc(t) { return String(t).replace(/\\/g, "\\\\").replace(/;/g, "\\;").replace(/,/g, "\\,").replace(/\r?\n/g, "\\n"); }
function icsFold(line) { const enc = new TextEncoder(); if (enc.encode(line).length <= 74) return line; let out = "", cur = ""; for (const ch of line) { if (enc.encode(cur + ch).length > 73) { out += (out ? "\r\n " : "") + cur; cur = ch; } else cur += ch; } return out + "\r\n " + cur; }
const icsTime = (iso) => new Date(iso).toISOString().replace(/[-:]/g, "").replace(/\.\d{3}/, "");
async function calendar(url, env) {
  let fx = await load(env, "api:v2:/api/fixtures?v=4");
  if (!fx.body) { const r = await refresh(env, "api:v2:/api/fixtures?v=4", ROUTES["/api/fixtures"], new URL("https://site.local/api/fixtures?v=4")); if (!r.ok) return json({ error: "fixtures unavailable" }, 503); fx = { body: r.body }; }   // never an empty feed: a subscribed calendar would drop its events
  const one = url.searchParams.get("m"), name = (t) => (t.id === TEAM ? "Ireland" : t.name).replace(/&apos;/g, "'"), origin = "https://irelandfootball.wiki", now = icsTime(new Date().toISOString());
  const list = (JSON.parse(fx.body).response || []).filter((f) => !/CANC|ABD|AWD|WO/.test(f.fixture.status.short) && (!one || String(f.fixture.id) === one)).sort((a, b) => a.fixture.timestamp - b.fixture.timestamp);
  if (one && !list.length) return new Response("No such fixture", { status: 404 });
  const L = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//irelandfootball.wiki//Fixtures//EN", "CALSCALE:GREGORIAN", "METHOD:PUBLISH"];
  if (!one) L.push("X-WR-CALNAME:Ireland football", "X-WR-CALDESC:" + icsEsc("Republic of Ireland men's fixtures from irelandfootball.wiki."), "X-WR-TIMEZONE:Europe/Dublin", "REFRESH-INTERVAL;VALUE=DURATION:PT6H", "X-PUBLISHED-TTL:PT6H");
  for (const f of list) {
    const st = f.fixture.status.short, done = /FT|AET|PEN/.test(st), unsure = /TBD|PST/.test(st), v = f.fixture.venue || {}, where = [v.name, v.city].filter(Boolean).join(", ");
    const title = done ? name(f.teams.home) + " " + f.goals.home + "–" + f.goals.away + " " + name(f.teams.away) : name(f.teams.home) + " v " + name(f.teams.away) + (st === "PST" ? " (postponed)" : unsure ? " (time to be confirmed)" : "");
    const start = new Date(f.fixture.date), desc = f.league.name + (f.league.round ? " · " + f.league.round : "") + "\n" + origin + "/match/?id=" + f.fixture.id;
    L.push("BEGIN:VEVENT", "UID:fixture-" + f.fixture.id + "@irelandfootball.wiki", "DTSTAMP:" + now, "DTSTART:" + icsTime(start.toISOString()), "DTEND:" + icsTime(new Date(start.getTime() + 115 * 60000).toISOString()), "SUMMARY:" + icsEsc(title), "STATUS:" + (unsure ? "TENTATIVE" : "CONFIRMED"));
    if (where) L.push("LOCATION:" + icsEsc(where));
    L.push("DESCRIPTION:" + icsEsc(desc), "CATEGORIES:" + icsEsc(f.league.name), "URL:" + origin + "/match/?id=" + f.fixture.id, "TRANSP:OPAQUE", "END:VEVENT");
  }
  L.push("END:VCALENDAR");
  return new Response(L.map(icsFold).join("\r\n") + "\r\n", { headers: { "content-type": "text/calendar; charset=utf-8", "cache-control": "public, max-age=1800", "content-disposition": (one ? "attachment" : "inline") + '; filename="' + (one ? "ireland-" + one : "ireland-fixtures") + '.ics"', "access-control-allow-origin": "*" } });
}

// Milestone alerts at full-time: caps (10, 25, 50, 100), goals (5, 10, 20 … 50) and places in the all-time top ten, for the
// players who appeared. Counts come from the archive; if the archive does not have this game yet, it is added on.
// Feed names are matched to the archive as the squad page does: surname, plus the initial when the feed gives one.
const CAP_MS = [10, 25, 50, 100], GOAL_MS = [5, 10, 20, 30, 40, 50];
async function milestones(env, f) {
  const get = (p) => env.ASSETS.fetch(new Request("https://irelandfootball.wiki" + p)).then((r) => r.json());
  const [P, M] = await Promise.all([get("/history/players.json"), get("/history/matches.json")]);
  const d = f.fixture.date.slice(0, 10), counted = M.some((m) => m.d === d);
  const us = (f.lineups || []).find((l) => l.team.id === TEAM); if (!us) return [];
  const slug = (s) => s.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  const arch = (n) => { const sn = slug(n.split(" ").pop()), ini = /^[A-Z]\./.test(n) ? n[0].toLowerCase() : null;
    return P.filter((h) => slug(h.name.split(" ").pop()) === sn && (!ini || h.name[0].toLowerCase() === ini) && h.last >= "2020").sort((x, y) => y.caps - x.caps)[0]; };
  const played = new Set(us.startXI.map((x) => x.player.name));
  for (const e of f.events || []) if (e.type === "subst" && e.team.id === TEAM) for (const x of [e.player, e.assist]) if (x && x.name) played.add(x.name);
  const goals = {}; for (const e of f.events || []) if (e.type === "Goal" && e.team.id === TEAM && e.detail !== "Own Goal" && e.detail !== "Missed Penalty" && e.player && e.player.name) goals[e.player.name] = (goals[e.player.name] || 0) + 1;
  const rank = (k, v, self) => P.filter((x) => x.slug !== self && x[k] > v).length + 1, out = [], seen = {};
  const th = (n) => n + (["th", "st", "nd", "rd"][(n % 100 - 20) % 10] || ["th", "st", "nd", "rd"][n % 100] || "th");
  for (const n of played) {
    const p = arch(n); if (!p || seen[p.slug]) continue; seen[p.slug] = 1;
    const c = p.caps + (counted ? 0 : 1), g0 = counted ? p.goals - (goals[n] || 0) : p.goals, g = g0 + (goals[n] || 0), what = [];
    if (CAP_MS.includes(c)) what.push(th(c) + " cap");
    const rc = rank("caps", c, p.slug), rc0 = rank("caps", c - 1, p.slug); if (rc <= 10 && rc < rc0) what.push("now " + th(rc) + " on the all-time caps list");
    for (const m of GOAL_MS) if (g0 < m && g >= m) what.push(th(m) + " Ireland goal");
    if (g > g0) { const rg = rank("goals", g, p.slug), rg0 = rank("goals", g0, p.slug); if (rg <= 10 && rg < rg0) what.push(rg === 1 ? "Ireland's record scorer" : "now " + th(rg) + " on the all-time scorers list"); }
    if (what.length) out.push({ name: p.name, what });
  }
  return out;
}

// A shared XI previews its title and the eleven names
async function xiMeta(html, env, u) {
  try {
    const P = await (await env.ASSETS.fetch(new Request(u.origin + "/history/players.json"))).json(), by = {}; for (const p of P) by[p.slug] = p.name;
    const names = (u.searchParams.get("p") || "").split(",").slice(0, 11).map((k) => by[k]).filter(Boolean);
    if (!names.length) return html;
    const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");
    const who = (u.searchParams.get("n") || "").slice(0, 30), title = (u.searchParams.get("t") || "").slice(0, 60) || (who ? who + "’s Ireland XI" : "An Ireland XI");
    const desc = (u.searchParams.get("f") || "") + " · " + names.join(", ") + ". Pick your own.";
    return html.replace(/<title>[^<]*<\/title>/, "<title>" + esc(title) + " · Ireland Football</title>")
      .replace(/<meta name="description" content="[^"]*">/, '<meta name="description" content="' + esc(desc) + '">')
      .replace(/<meta property="og:title" content="[^"]*">/, '<meta property="og:title" content="' + esc(title) + '">')
      .replace(/<meta property="og:description" content="[^"]*">/, '<meta property="og:description" content="' + esc(desc) + '">');
  } catch (e) { return html }
}

// "Ireland in your lifetime": a shared link previews the sender's numbers (WhatsApp, iMessage, Slack read these tags)
async function lifetimeMeta(html, y, env, u) {
  try {
    const L = await (await env.ASSETS.fetch(new Request(u.origin + "/history/matches.json"))).json();
    const from = Math.max(y, 1924), S = L.filter(m => +m.d.slice(0, 4) >= from);
    if (y > new Date().getFullYear() || !S.length) return html;
    const w = S.filter(m => m.gf > m.ga), big = w.slice().sort((a, b) => (b.gf - b.ga) - (a.gf - a.ga) || b.gf - a.gf || (a.d < b.d ? -1 : 1))[0];
    const esc = s => String(s).replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");
    const title = "Ireland since " + y;
    const won = S.filter(m => m.pw != null ? m.pw : m.gf > m.ga).length;  // a shoot-out win counts as a win, as on the page
    const desc = S.length + " games, " + won + " won" + (big ? ". Biggest win: " + big.gf + "–" + big.ga + " v " + big.o + ", " + big.d.slice(0, 4) : "") + ". Enter your own birth year.";
    return html.replace(/<title>[^<]*<\/title>/, "<title>" + esc(title) + " · Ireland Football</title>")
      .replace(/<meta name="description" content="[^"]*">/, '<meta name="description" content="' + esc(desc) + '">')
      .replace(/<meta property="og:title" content="[^"]*">/, '<meta property="og:title" content="' + esc(title) + '">')
      .replace(/<meta property="og:description" content="[^"]*">/, '<meta property="og:description" content="' + esc(desc) + '">');
  } catch (e) { return html }
}

// Pages and data files. HTML gets the visitor's country for "where to watch" and consent later, so it is never shared from the edge cache.
async function page(request, env) {
  const res = await env.ASSETS.fetch(request);
  const ct = res.headers.get("content-type") || "";
  if (!/text\/html/.test(ct)) return res;
  let html = await res.text();
  const u = new URL(request.url);
  if (u.pathname === "/lifetime/" && /^\d{4}$/.test(u.searchParams.get("y") || "")) html = await lifetimeMeta(html, +u.searchParams.get("y"), env, u);
  if (u.pathname === "/xi/" && u.searchParams.get("p")) html = await xiMeta(html, env, u);
  const body = html.replace("<head>", '<head><meta name="mu-country" content="' + ((request.cf && request.cf.country) || "").replace(/[^A-Z]/g, "") + '">' + LANG_HEAD);
  const h = new Headers(res.headers); h.delete("content-length"); h.set("cache-control", "private, max-age=0, must-revalidate");
  if (env.UPSTREAM) h.set("x-robots-tag", "noindex");   // the dev site stays out of search
  return new Response(body, { status: res.status, headers: h });
}

async function load(env, key) {
  const raw = await env.MU_CACHE.get(key);
  if (!raw) return { body: null };
  const nl = raw.indexOf("\n");
  const stamp = parseInt(raw.slice(0, nl), 10);   // first line: unix seconds when fetched + ttl
  const ttl = parseInt(raw.slice(nl + 1, raw.indexOf("\n", nl + 1)), 10);
  const body = raw.slice(raw.indexOf("\n", nl + 1) + 1);
  const age = Math.floor(Date.now() / 1000) - stamp;
  return { body, fresh: age < ttl, age };
}

// Fetch from API-Football with a few retries on the per-minute cap; store only clean answers.

// Fetch from API-Football with a few retries on the per-minute cap; store only clean answers.
// A route with several paths is one answer: their response arrays are joined.
async function fetchOne(env, path) {
  let upstream, body = "";
  for (let attempt = 0; attempt < 4; attempt++) {
    try {
      upstream = await fetch(API + path, { headers: { "x-apisports-key": env.API_FOOTBALL_KEY }, cf: { cacheTtl: 0 } });
      body = await upstream.text();
    } catch (e) { body = JSON.stringify({ errors: { network: String(e) } }); }
    if (!/"rateLimit"/.test(body)) break;
    await sleep(1500 + attempt * 1500);
  }
  let clean = false, j = null;
  try { j = JSON.parse(body); clean = !!upstream && upstream.ok && j && (Array.isArray(j.errors) ? j.errors.length === 0 : Object.keys(j.errors || {}).length === 0) && !j.message; } catch (e) {}
  return { clean, j, body };
}
// The team filter on /standings returns only Ireland's row, so it is used to find the competition, then the whole
// competition is fetched and cut down to Ireland's group. The feed letters Nations League groups (League B - Group C);
// UEFA numbers them, so the label is rewritten to match (League B, Group 3).
async function standings(env) {
  const out = [];
  for (const s of seasons()) {
    const a = await fetchOne(env, `/standings?team=${TEAM}&season=${s}`);
    if (!a.clean) return { ok: false, body: a.body };
    for (const r of a.j.response || []) {
      const b = await fetchOne(env, `/standings?league=${r.league.id}&season=${r.league.season}`);
      if (!b.clean) return { ok: false, body: b.body };
      for (const l of b.j.response || []) {
        const groups = (l.league.standings || []).filter((g) => g.some((x) => x.team.id === TEAM));
        groups.forEach((g) => g.forEach((x) => { x.group = String(x.group || "").replace(/League ([A-D]) - Group ([A-D])/, (_, L, G) => `League ${L}, Group ${G.charCodeAt(0) - 64}`); }));
        out.push({ league: Object.assign({}, l.league, { standings: groups }) });
      }
    }
  }
  return { ok: true, body: JSON.stringify({ errors: [], results: out.length, response: out }) };
}
async function refresh(env, key, route, url) {
  if (route.custom) {
    const r = await route.custom(env);
    if (r.ok) await env.MU_CACHE.put(key, Math.floor(Date.now() / 1000) + "\n" + route.ttl + "\n" + r.body, { expirationTtl: route.ttl + KEEP });
    return r;
  }
  const paths = route.paths ? route.paths(url) : [route.path(url)];
  const parts = []; for (const p of paths) parts.push(await fetchOne(env, p));
  const bad = parts.find((x) => !x.clean);
  if (bad) return { ok: false, body: bad.body };
  const body = parts.length === 1 ? parts[0].body : JSON.stringify({ errors: [], results: parts.reduce((n, x) => n + (x.j.response || []).length, 0), response: parts.flatMap((x) => x.j.response || []) });
  await env.MU_CACHE.put(key, Math.floor(Date.now() / 1000) + "\n" + route.ttl + "\n" + body, { expirationTtl: route.ttl + KEEP });
  return { ok: true, body };
}

function headers(src, age) {
  return { "content-type": "application/json; charset=utf-8", "cache-control": "public, max-age=120", "access-control-allow-origin": "*", "x-source": src, "x-age": String(age || 0) };
}
function answer(body, src, age) { return new Response(body, { status: 200, headers: headers(src, age) }); }
function json(obj, status = 200) { return new Response(JSON.stringify(obj), { status, headers: headers("worker") }); }
function sleep(ms) { return new Promise((r) => setTimeout(r, ms)); }

// so the team-picker's PNG export can draw them. No API quota is used for these.
async function portrait(url, ctx) {
  const m = url.pathname.match(/^\/img\/player\/(\d+)\.png$/);
  if (!m) return new Response("not found", { status: 404 });
  const cache = caches.default, key = new Request(url.origin + "/__img/v1/" + m[1]);
  const hit = await cache.match(key);
  if (hit) return hit;
  const up = await fetch("https://media.api-sports.io/football/players/" + m[1] + ".png", { cf: { cacheTtl: 86400 } });
  if (!up.ok) return new Response("not found", { status: 404 });
  const res = new Response(up.body, { status: 200, headers: { "content-type": "image/png", "cache-control": "public, max-age=86400", "access-control-allow-origin": "*" } });
  ctx.waitUntil(cache.put(key, res.clone()));
  return res;
}


// ---- Wikipedia player profile → JSON (summary + parsed football-biography infobox), cached 7 days.
async function wiki(url, env, ctx) {
  let title = (url.searchParams.get("title") || "").trim(), q = (url.searchParams.get("q") || "").trim();
  if (!title && !q) return json({ error: "title or q required" }, 400);
  const UA = { "user-agent": "irelandfootball/1.0 (richardmcallister@gmail.com)", "accept": "application/json" };
  if (!title) {
    // Resolve an abbreviated name ("K. Mainoo") to an article title via search.
    const qkey = "wiki:q:v4:" + q.toLowerCase();
    let hit = await env.MU_CACHE.get(qkey);
    if (!hit) {
      const surname = q.replace(/^[A-Z]\. ?/, "").split(" ").pop();
      const r = await fetch("https://en.wikipedia.org/w/api.php?action=query&list=search&format=json&srlimit=5&srsearch=" + encodeURIComponent('hastemplate:"Infobox football biography" ' + q.replace(/^[A-Z]\. ?/, "") + " Republic of Ireland national football team"), { headers: UA });
      const j = r.ok ? await r.json() : null;
      const list = j && j.query ? j.query.search : [];
      // Surname must be a whole word of the title (so "O. Martin" cannot land on "Martin Dúbravka"), and when the query
      // carries an initial the title's first name must start with it; fall back to the plain surname match, then nothing.
      const ini = (q.match(/^([A-Z])\. ?/) || [])[1], sn = surname.toLowerCase(), base = (t) => t.replace(/\s*\(.*\)$/, "");
      const word = (t) => base(t).toLowerCase().split(/[\s-]+/).indexOf(sn) >= 0 && base(t).toLowerCase().split(/[\s-]+/).indexOf(sn) > 0;
      const pick = list.filter((x) => word(x.title) && (!ini || base(x.title)[0].toUpperCase() === ini))[0] || (!ini ? (list.filter((x) => word(x.title))[0] || list.filter((x) => x.title.toLowerCase().indexOf(sn) >= 0)[0]) : null);
      hit = pick ? pick.title : "";
      if (hit) ctx.waitUntil(env.MU_CACHE.put(qkey, hit, { expirationTtl: 30 * 86400 }));
    }
    if (!hit) return json({ error: "not found", q }, 404);
    title = hit;
  }
  const key = "wiki:p:v10:" + title;
  const cached = url.searchParams.get("debug") ? null : await env.MU_CACHE.get(key);
  if (cached) return new Response(cached, { headers: headers("kv-hit") });
  const enc = encodeURIComponent(title.replace(/ /g, "_"));
  const [sr, wr, ir] = await Promise.all([
    fetch("https://en.wikipedia.org/api/rest_v1/page/summary/" + enc, { headers: UA }),
    fetch("https://en.wikipedia.org/w/api.php?action=parse&format=json&prop=wikitext&redirects=1&page=" + enc, { headers: UA }),
    fetch("https://en.wikipedia.org/w/api.php?action=query&format=json&redirects=1&generator=images&gimlimit=30&prop=imageinfo&iiprop=url|mime&iiurlwidth=640&titles=" + enc, { headers: UA }),
  ]);
  let sum = sr.ok ? await sr.json() : {};
  let wj = wr.ok ? await wr.json() : {};
  let ij = ir.ok ? await ir.json() : {};
  let wt = wj.parse && wj.parse.wikitext ? wj.parse.wikitext["*"] : "";
  let box = parseInfobox(wt);
  if ((sum.type === "disambiguation" || !box) && !url.searchParams.get("noretry")) {
    // Wrong article (a disambiguation page, or no football infobox): try the "(footballer)" title, then a biography search.
    const tries = [title + " (footballer)", title + " (Irish footballer)", title + " (Scottish footballer)", title + " (English footballer)"];
    let found = null;
    for (const t of tries) {
      const r = await fetch("https://en.wikipedia.org/api/rest_v1/page/summary/" + encodeURIComponent(t.replace(/ /g, "_")), { headers: UA });
      if (r.ok) { const j = await r.json(); if (j.type !== "disambiguation" && /footballer|football manager|football player|soccer/i.test(j.description || "")) { found = j.title; break; } }
    }
    if (!found) {
      const r = await fetch("https://en.wikipedia.org/w/api.php?action=query&list=search&format=json&srlimit=5&srsearch=" + encodeURIComponent('hastemplate:"Infobox football biography" "' + title.replace(/ \(.*\)$/, "") + '" Republic of Ireland'), { headers: UA });
      const j = r.ok ? await r.json() : null; const hit = j && j.query && j.query.search[0];
      if (hit) found = hit.title;
    }
    if (found && found !== title) { const u2 = new URL(url.toString()); u2.searchParams.set("title", found); u2.searchParams.set("noretry", "1"); return wiki(u2, env, ctx); }
  }
  if (url.searchParams.get("debug")) { const i0 = wt.search(/\{\{\s*Infobox football biography/i); return json({ keys: box && box._keys, raw: wt.slice(i0, i0 + 6000) }); }
  // Photos from the article: real photographs only (no SVG icons, flags, crests, maps).
  const images = Object.values((ij.query && ij.query.pages) || {}).filter((pg) => pg.imageinfo && pg.imageinfo[0] && /image\/(jpeg|png)/.test(pg.imageinfo[0].mime) && !/flag|logo|crest|badge|icon|map|kit|shirt|signature|wikimedia|commons-logo|stadium/i.test(pg.title))
    .map((pg) => ({ title: pg.title.replace(/^File:/, ""), thumb: pg.imageinfo[0].thumburl || pg.imageinfo[0].url, url: pg.imageinfo[0].descriptionurl || pg.imageinfo[0].url })).slice(0, 12);
  const out = { title: sum.title || title, description: sum.description || "", extract: sum.extract || "", thumbnail: sum.thumbnail ? sum.thumbnail.source : "", thumb: sum.thumbnail ? { w: sum.thumbnail.width, h: sum.thumbnail.height, ow: sum.originalimage && sum.originalimage.width || 0 } : null, original: sum.originalimage ? sum.originalimage.source : "", url: sum.content_urls ? sum.content_urls.desktop.page : "https://en.wikipedia.org/wiki/" + enc, infobox: box, images };
  const body = JSON.stringify(out);
  if (sum.title) ctx.waitUntil(env.MU_CACHE.put(key, body, { expirationTtl: 7 * 86400 }));
  return new Response(body, { headers: headers(sum.title ? "upstream" : "upstream-empty") });
}
function boxFields(wt, re) {
  const i = wt.search(re);
  if (i < 0) return null;
  let depth = 0, j = i;
  for (; j < wt.length; j++) { if (wt.startsWith("{{", j)) { depth++; j++; } else if (wt.startsWith("}}", j)) { depth--; j++; if (depth === 0) break; } }
  const body = wt.slice(i + 2, j - 1);
  const parts = []; let cur = "", d = 0, b = 0;
  for (let k = 0; k < body.length; k++) {
    const c2 = body.substr(k, 2);
    if (c2 === "{{") { d++; cur += c2; k++; continue; } if (c2 === "}}") { d--; cur += c2; k++; continue; }
    if (c2 === "[[") { b++; cur += c2; k++; continue; } if (c2 === "]]") { b--; cur += c2; k++; continue; }
    if (body[k] === "|" && d === 0 && b === 0) { parts.push(cur); cur = ""; continue; }
    cur += body[k];
  }
  parts.push(cur);
  const f = {};
  parts.slice(1).forEach((p) => { const m = p.match(/^\s*([\w\- ]+?)\s*=\s*([\s\S]*)$/); if (m) f[m[1].toLowerCase().replace(/[_\s]/g, "")] = wtClean(m[2]); });
  return f;
}
function parseInfobox(wt) {
  const f = boxFields(wt, /\{\{\s*Infobox football biography/i);
  if (!f) return null;
  if (f.embed) {
    // Football box embedded in a general biography box (actors, pundits…): personal details live in the outer box.
    const outer = boxFields(wt, /\{\{\s*Infobox (?:person|sportsperson|football official)/i) || {};
    ["name", "fullname", "birthname", "birthdate", "birthplace", "deathdate", "height"].forEach((k) => { if (!f[k] && outer[k]) f[k] = outer[k]; });
    if (!f.fullname && outer.birthname) f.fullname = outer.birthname;
  }
  const rows = (pre, keys) => { const out = []; for (let n = 1; n < 40; n++) { const r = {}; let any = false; keys.forEach((k) => { const v = f[pre + k + n]; if (v !== undefined && v !== "") any = true; r[k] = v || ""; }); if (!any) { if (n > 3) break; else continue; } if (r.clubs || r.team) out.push(r); } return out; };
  return {
    _keys: Object.keys(f),
    name: f.name || "", fullname: f.fullname || "", birth_date: f.birthdate || "", birth_place: f.birthplace || "", death_date: f.deathdate || "", height: f.height || "", position: f.position || "", currentclub: f.currentclub || "", clubnumber: f.clubnumber || "",
    youth: rows("youth", ["years", "clubs"]), clubs: rows("", ["years", "clubs", "caps", "goals"]), national: rows("national", ["years", "team", "caps", "goals"]), manager: rows("manager", ["years", "clubs"]),
    totalcaps: f.totalcaps || "", totalgoals: f.totalgoals || "",
  };
}
// Reduce wikitext to plain text: refs out, links to their label, common templates to their value.
function wtClean(v) {
  let s = String(v);
  s = s.replace(/<ref[^>]*\/>/g, "").replace(/<ref[\s\S]*?<\/ref>/g, "").replace(/<!--[\s\S]*?-->/g, "").replace(/<br\s*\/?>/gi, " ");
  for (let n = 0; n < 4; n++) {
    s = s.replace(/\{\{\s*(?:birth date and age|birth date|death date and age|death date|bda|dda|birth-date and age|birth-date)\s*\|([^}]*)\}\}/gi, (m, args) => { const n = args.split("|").map((x) => x.trim()).filter((x) => /^\d+$/.test(x)); return n.length >= 3 ? n[0] + "-" + n[1].padStart(2, "0") + "-" + n[2].padStart(2, "0") : (n[0] || ""); });
    s = s.replace(/\{\{\s*(?:birth year and age|death year and age)\s*\|\s*(\d{4})[^}]*\}\}/gi, "$1");
    s = s.replace(/\{\{\s*(?:convert|cvt)\s*\|\s*(\d+)\s*\|\s*ft\s*\|\s*([\d.]+)\s*\|\s*in[^}]*\}\}/gi, (m, ft, inch) => ((parseInt(ft, 10) * 12 + parseFloat(inch)) * 0.0254).toFixed(2) + " m");
    s = s.replace(/\{\{\s*height\s*\|[^}]*ft\s*=\s*(\d+)[^}]*in\s*=\s*([\d.]+)[^}]*\}\}/gi, (m, ft, inch) => ((parseInt(ft, 10) * 12 + parseFloat(inch)) * 0.0254).toFixed(2) + " m");
    s = s.replace(/\{\{\s*(?:height|convert|cvt)\s*\|\s*(?:m\s*=\s*)?([\d.]+)\s*(?:\|\s*m)?[^}]*\}\}/gi, (m, x) => (parseFloat(x) < 3 ? x + " m" : x));
    s = s.replace(/\{\{\s*(?:nowrap|nobr|nobold|nbsp|small|lang|flagicon|flagu|flag|fb|fbu|fbw|plainlist|hlist|ubl|unbulleted list|dts|date|start date|end date)\s*\|([^{}]*)\}\}/gi, (m, x) => x.split("|").filter((p) => !/=/.test(p)).join(" · "));
    s = s.replace(/\{\{\s*0\s*\|[^{}]*\}\}/g, "");          // {{0|0000}} spacing pad
    s = s.replace(/\{\{\s*[^{}|]*\s*\}\}/g, "");
  }
  for (let n = 0; n < 5 && /\{\{/.test(s); n++) s = s.replace(/\{\{[^{}]*\}\}/g, "");   // anything else left over, innermost first
  s = s.replace(/\[\[(?:[^\]|]*\|)?([^\]]*)\]\]/g, "$1").replace(/\[https?:[^\s\]]*\s?([^\]]*)\]/g, "$1");
  s = s.replace(/'{2,}/g, "").replace(/<[^>]+>/g, "").replace(/&nbsp;/g, " ").replace(/\s+/g, " ").trim();
  return s;
}


// ---- Academy & loan watch: one composite report, cached in KV, rebuilt by the cron and on demand when stale.

// ---- raw wikitext of one article (cached a day) — used by the build scripts that compile squad numbers.
async function wikiRaw(url, env, ctx) {
  const title = (url.searchParams.get("title") || "").trim(); if (!title) return json({ error: "title required" }, 400);
  const rev = (url.searchParams.get("rev") || "").replace(/\D/g, "");   // build scripts pass the revision they expect, so a changed article is never served from cache
  const key = "wiki:raw:v1:" + title + (rev ? "@" + rev : ""), cached = await env.MU_CACHE.get(key);
  if (cached) return new Response(cached, { headers: { "content-type": "text/plain; charset=utf-8", "x-source": "kv-hit" } });
  const UA = { "user-agent": "irelandfootball/1.0 (richardmcallister@gmail.com)", "accept": "application/json" };
  const r = await fetch("https://en.wikipedia.org/w/api.php?action=parse&format=json&prop=wikitext&redirects=1&page=" + encodeURIComponent(title.replace(/ /g, "_")), { headers: UA });
  const j = r.ok ? await r.json() : {};
  const wt = j.parse && j.parse.wikitext ? j.parse.wikitext["*"] : "";
  if (!wt) return json({ error: "no article", title }, 404);
  ctx.waitUntil(env.MU_CACHE.put(key, wt, { expirationTtl: 86400 }));
  return new Response(wt, { headers: { "content-type": "text/plain; charset=utf-8", "x-source": "upstream" } });
}


// Plain article summary (lead paragraph, thumbnail, link) for any title — rivalry articles and the like; a week in KV.
