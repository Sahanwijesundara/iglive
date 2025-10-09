// ==UserScript==
// @name         IG Live Detector - Minimal Safe Upsert (Supabase REST)
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  Detect IG LIVE and safely upsert minimal payload to Supabase REST. Sends only username/link/is_live to avoid timestamp/text type errors. WARNING: includes keys - for personal testing only.
// @match        https://www.instagram.com/*
// @grant        GM_xmlhttpRequest
// @run-at       document-start
// ==/UserScript==

(function() {
    'use strict';

    /********** CONFIG (from your earlier snippets) **********/
    const DATABASE_URL = "https://dwusirnnyxcjqwmaaibg.supabase.co/rest/v1/insta_links";
    const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImR3dXNpcm5ueXhjanF3bWFhaWJnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTk2NTY2MDEsImV4cCI6MjA3NTIzMjYwMX0.cZVnLK3fCwCpTjQ_cbsl6DZVqREnM_LMsyMIAnYbYd4";
    const SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImR3dXNpcm5ueXhjanF3bWFhaWJnIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1OTY1NjYwMSwiZXhwIjoyMDc1MjMyNjAxfQ.keAtvVn0q3vStvA1EXGoUtKeURLTuSJ7sJ5dnWw63LQ";
    // Choose which key to use here. SERVICE key gives full powers, ANON is safer (but requires RLS/policies).
    const AUTH_KEY_TO_USE = SUPABASE_SERVICE_KEY; // or SUPABASE_ANON_KEY
    const CHECK_INTERVAL = 3000; // ms
    const MIN_UPDATE_INTERVAL_PER_USER = 12 * 1000; // ms between DB updates per username
    /*******************************************************/

    // internal state
    let previouslyLive = new Set();
    const lastUpdateTs = new Map();
    let dbUpdateCount = 0;

    function nowIso() { return (new Date()).toISOString(); }

    function canUpdateUsername(username) {
        const last = lastUpdateTs.get(username) || 0;
        if (Date.now() - last < MIN_UPDATE_INTERVAL_PER_USER) return false;
        lastUpdateTs.set(username, Date.now());
        return true;
    }

    // PRIMARY: minimal payload only to avoid type mismatches server-side
    function makePayloadMinimal(username, isLive) {
        return {
            username: username,
            link: `https://instagram.com/${username}`,
            is_live: !!isLive
            // NOTE: intentionally NOT sending last_updated or last_live_at to avoid text/timestamp mismatches.
            // rely on DB default NOW() for last_updated if you have DEFAULT now() in table.
        };
    }

    // Upsert (POST array) then fallback to PATCH on 409.
    function upsertSafe(payloadObj, cb) {
        const body = JSON.stringify([payloadObj]); // array required for PostgREST bulk upsert

        GM_xmlhttpRequest({
            method: 'POST',
            url: DATABASE_URL,
            headers: {
                'apikey': AUTH_KEY_TO_USE,
                'Authorization': `Bearer ${AUTH_KEY_TO_USE}`,
                'Content-Type': 'application/json',
                'Prefer': 'resolution=merge-duplicates,return=representation'
            },
            data: body,
            onload: function(resp) {
                // If server returns 200..299 -> success
                if (resp.status >= 200 && resp.status < 300) {
                    dbUpdateCount++;
                    updateDebugUI();
                    logActivity(`Upserted @${payloadObj.username}`, 'success');
                    if (cb) cb(null, resp);
                    return;
                }

                // 409 -> conflict -> try PATCH by username
                if (resp.status === 409) {
                    logActivity(`409 conflict for @${payloadObj.username} — trying PATCH`, 'info');
                    tryPatchMinimal(payloadObj, cb);
                    return;
                }

                // 404 + Postgres error body indicating operator mismatch -> log details and stop sending timestamps
                if (resp.status === 404 && resp.responseText && resp.responseText.includes('operator does not exist')) {
                    logActivity(`Server error (operator mismatch) for @${payloadObj.username}: ${resp.responseText}`, 'error');
                    // we already omitted timestamps — but show full server error in UI for debugging
                    if (cb) cb(new Error('operator_mismatch'), resp);
                    return;
                }

                // Other errors -> log
                logActivity(`POST error @${payloadObj.username}: ${resp.status} ${resp.responseText}`, 'error');
                if (cb) cb(new Error(`POST ${resp.status}`), resp);
            },
            onerror: function(err) {
                logActivity(`Network POST error @${payloadObj.username}`, 'error');
                if (cb) cb(err, null);
            }
        });
    }

    function tryPatchMinimal(payloadObj, cb) {
        const patchPayload = {
            is_live: payloadObj.is_live,
            // intentionally not touching timestamp fields here
            link: payloadObj.link
        };
        const patchUrl = `${DATABASE_URL}?username=eq.${encodeURIComponent(payloadObj.username)}`;

        GM_xmlhttpRequest({
            method: 'PATCH',
            url: patchUrl,
            headers: {
                'apikey': AUTH_KEY_TO_USE,
                'Authorization': `Bearer ${AUTH_KEY_TO_USE}`,
                'Content-Type': 'application/json',
                'Prefer': 'return=representation'
            },
            data: JSON.stringify(patchPayload),
            onload: function(resp) {
                if (resp.status >= 200 && resp.status < 300) {
                    dbUpdateCount++;
                    updateDebugUI();
                    logActivity(`Patched @${payloadObj.username}`, 'success');
                    if (cb) cb(null, resp);
                } else {
                    logActivity(`PATCH failed @${payloadObj.username}: ${resp.status} ${resp.responseText}`, 'error');
                    if (cb) cb(new Error(`PATCH ${resp.status}`), resp);
                }
            },
            onerror: function(err) {
                logActivity(`Network PATCH error @${payloadObj.username}`, 'error');
                if (cb) cb(err, null);
            }
        });
    }

    // updateDatabase uses the minimal safe payload
    function updateDatabase(username, isLive) {
        if (!canUpdateUsername(username)) {
            logActivity(`Skipped DB update for @${username} (rate-limited)`, 'info');
            return;
        }
        const payload = makePayloadMinimal(username, isLive);
        upsertSafe(payload, function(err, resp) {
            if (err) {
                console.error('DB update error', err, resp && resp.responseText);
            }
        });
    }

    // Extract username robustly from aria-label; fallback heuristics kept
    function extractUsername(ariaLabel) {
        if (!ariaLabel) return null;
        let m = ariaLabel.match(/Story by\s+([^,]+)/i);
        if (m) return m[1].trim();
        m = ariaLabel.match(/^([^'’\s]+)[’']s story/i);
        if (m) return m[1].trim();
        return (ariaLabel.split(/\s+/)[0] || '').replace(/[^a-zA-Z0-9._]/g,'').trim();
    }

    // Detect live stories: broad selector + check for "LIVE" text
    function detectLiveStories() {
        try {
            const items = document.querySelectorAll('ul li');
            if (!items || items.length === 0) return;

            const currentlyLive = new Set();

            items.forEach(item => {
                const button = item.querySelector('div[role="button"][aria-label]');
                if (!button) return;
                const aria = button.getAttribute('aria-label') || '';

                const hasLive = Array.from(item.querySelectorAll('span')).some(s => {
                    const t = (s.textContent || '').trim().toUpperCase();
                    return t === 'LIVE' || t === 'LIVE NOW';
                });

                if (hasLive) {
                    const username = extractUsername(aria);
                    if (username) {
                        currentlyLive.add(username);
                        if (!previouslyLive.has(username)) {
                            console.log(`🔴 NEW LIVE: ${username}`);
                            updateDatabase(username, true);
                        }
                    }
                }
            });

            // detect ended
            previouslyLive.forEach(u => {
                if (!currentlyLive.has(u)) {
                    console.log(`⚫ ENDED: ${u}`);
                    updateDatabase(u, false);
                }
            });

            previouslyLive = currentlyLive;
            updateDebugUI();
        } catch (err) {
            console.error('detectLiveStories error', err);
        }
    }

    /****************** DEBUG UI ******************/
    function createDebugUI() {
        if (document.getElementById('ig-live-debug')) return;
        const debugPanel = document.createElement('div');
        debugPanel.id = 'ig-live-debug';
        debugPanel.style = 'position:fixed;top:10px;right:10px;background:rgba(0,0,0,0.92);color:#fff;padding:12px;border-radius:8px;z-index:9999999;font-family:monospace;font-size:12px;max-width:360px;box-shadow:0 8px 24px rgba(0,0,0,0.6);';
        debugPanel.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                <strong style="color:#00ff00">🔴 Live Detector (Safe)</strong>
                <button id="ig-debug-toggle" style="background:#333;color:#fff;border:none;padding:2px 6px;border-radius:4px;cursor:pointer;">−</button>
            </div>
            <div id="ig-debug-content">
                <div style="margin-bottom:6px;"><span style="color:#888">Status:</span> <span id="ig-status" style="color:#00ff00;margin-left:6px">●</span> <span id="ig-status-text" style="margin-left:6px">Running</span></div>
                <div style="margin-bottom:6px;"><span style="color:#888">Live Now:</span> <span id="ig-live-count" style="color:#ff6b6b;margin-left:6px;font-weight:bold">0</span></div>
                <div style="margin-bottom:6px;"><span style="color:#888">DB Updates:</span> <span id="ig-db-updates" style="color:#7aa2ff;margin-left:6px;font-weight:bold">0</span></div>
                <div style="border-top:1px solid #333;padding-top:8px;margin-top:8px;">
                    <div style="color:#888;margin-bottom:6px">Live Users:</div>
                    <div id="ig-live-list" style="max-height:140px;overflow-y:auto;font-size:11px;color:#ffd6d6"><div style="color:#666;font-style:italic">No one live yet...</div></div>
                </div>
                <div style="border-top:1px solid #333;padding-top:8px;margin-top:8px;">
                    <div style="color:#888;margin-bottom:6px">Recent Activity:</div>
                    <div id="ig-activity-log" style="max-height:160px;overflow-y:auto;font-size:10px;color:#ddd;"><div style="color:#666">Waiting for activity...</div></div>
                </div>
            </div>
        `;
        document.body.appendChild(debugPanel);

        document.getElementById('ig-debug-toggle').addEventListener('click', function() {
            const content = document.getElementById('ig-debug-content');
            const btn = this;
            if (content.style.display === 'none') {
                content.style.display = 'block'; btn.textContent = '−';
            } else {
                content.style.display = 'none'; btn.textContent = '+';
            }
        });
    }

    function updateDebugUI() {
        const liveCount = document.getElementById('ig-live-count');
        const liveList = document.getElementById('ig-live-list');
        const dbCounter = document.getElementById('ig-db-updates');
        if (liveCount) liveCount.textContent = previouslyLive.size;
        if (dbCounter) dbCounter.textContent = dbUpdateCount;
        if (liveList) {
            if (previouslyLive.size === 0) {
                liveList.innerHTML = '<div style="color:#666;font-style:italic">No one live yet...</div>';
            } else {
                liveList.innerHTML = Array.from(previouslyLive).map(u => `<div style="padding:4px 0;color:#ff9b9b">🔴 @${u}</div>`).join('');
            }
        }
    }

    function logActivity(message, type='info') {
        const activityLog = document.getElementById('ig-activity-log');
        if (!activityLog) return;
        const time = new Date().toLocaleTimeString();
        const colors = {'info':'#aaa','success':'#8ef58e','error':'#ff8b8b'};
        const entry = document.createElement('div');
        entry.style.color = colors[type] || '#aaa';
        entry.style.padding = '2px 0';
        entry.textContent = `[${time}] ${message}`;
        if (activityLog.children.length >= 20) activityLog.removeChild(activityLog.firstChild);
        activityLog.appendChild(entry);
        activityLog.scrollTop = activityLog.scrollHeight;
    }
    /*****************************************************/

    function init() {
        console.log('🚀 IG Live Detector (safe upsert) started');
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                createDebugUI();
                startMonitoring();
            });
        } else {
            createDebugUI();
            startMonitoring();
        }
    }

    function startMonitoring() {
        logActivity('Debug UI initialized', 'info');
        detectLiveStories();
        setInterval(detectLiveStories, CHECK_INTERVAL);
    }

    // SPA navigation handling
    let lastUrl = location.href;
    new MutationObserver(() => {
        const currentUrl = location.href;
        if (currentUrl !== lastUrl) {
            lastUrl = currentUrl;
            previouslyLive.clear();
            setTimeout(startMonitoring, 800);
        }
    }).observe(document, { subtree: true, childList: true });

    init();
})();
