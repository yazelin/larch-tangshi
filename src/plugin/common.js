/* 卡片共用：跟 Larch 溝通。
   編輯器預覽不送 init，2 秒後用 window.SAMPLE 進「預覽模式」：畫面照常，但不送出任何寫入（set/complete）。
   正式 init 晚到（慢手機）時，把資料存進 window.name 再重載，重載後直接用正式資料啟動，不會被範例資料劫持。 */
var L = (function () {
  var initFns = [], vars = {}, started = false, finished = false, preview = false, KEY = 'tangshi-init:';
  function start(script, v) {
    if (started) return; started = true; vars = v || {};
    initFns.forEach(function (f) { f(script, vars); });
  }
  function fromInit(d) {
    var s = {}; try { s = JSON.parse((d.values || {}).script || '{}'); } catch (err) {}
    return { script: s, variables: d.variables || {} };
  }
  addEventListener('message', function (e) {
    var d = e.data; if (!d || d.type !== 'larch:init') return;
    var got = fromInit(d);
    if (preview) {   // 已經用範例資料起來了：存起來重載，乾淨地換成正式資料
      try { window.name = KEY + JSON.stringify(got); location.reload(); } catch (err) {}
      return;
    }
    start(got.script, got.variables);
  });
  var saved = null;
  try { if (window.name.indexOf(KEY) === 0) { saved = JSON.parse(window.name.slice(KEY.length)); window.name = ''; } } catch (err) {}
  if (saved) setTimeout(function () { start(saved.script, saved.variables); }, 0);
  else {
    parent.postMessage({ type: 'larch:ready' }, '*');
    setTimeout(function () { if (!started) { preview = true; start(window.SAMPLE || {}, {}); } }, 2000);
  }
  return {
    onInit: function (f) { initFns.push(f); },
    set: function (n, v) { vars[n] = v; if (!preview) parent.postMessage({ type: 'larch:set', name: n, value: v }, '*'); },
    get: function (n, dflt) { return (n in vars && vars[n] !== '' && vars[n] != null) ? vars[n] : dflt; },
    done: function () { if (finished || preview) return; finished = true; parent.postMessage({ type: 'larch:complete' }, '*'); },
    play: function (url, from, dur) {
      if (!url) return null;
      var a = new Audio(url); a.currentTime = from || 0; a.play().catch(function () {});
      if (dur) setTimeout(function () { a.pause(); }, dur * 1000);
      return a;
    }
  };
})();
