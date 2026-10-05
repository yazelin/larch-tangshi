/* 卡片共用：跟 Larch 溝通。編輯器預覽不送 init，2 秒後用 window.SAMPLE 自己啟動。 */
var L = (function () {
  var initFns = [], vars = {}, started = false, finished = false;
  function start(script, v) {
    if (started) return; started = true; vars = v || {};
    initFns.forEach(function (f) { f(script, vars); });
  }
  addEventListener('message', function (e) {
    var d = e.data; if (!d || d.type !== 'larch:init') return;
    var s = {}; try { s = JSON.parse((d.values || {}).script || '{}'); } catch (err) {}
    start(s, d.variables);
  });
  parent.postMessage({ type: 'larch:ready' }, '*');
  setTimeout(function () { start(window.SAMPLE || {}, {}); }, 2000);
  return {
    onInit: function (f) { initFns.push(f); },
    set: function (n, v) { vars[n] = v; parent.postMessage({ type: 'larch:set', name: n, value: v }, '*'); },
    get: function (n, dflt) { return (n in vars && vars[n] !== '' && vars[n] != null) ? vars[n] : dflt; },
    done: function () { if (finished) return; finished = true; parent.postMessage({ type: 'larch:complete' }, '*'); },
    play: function (url, from, dur) {
      if (!url) return null;
      var a = new Audio(url); a.currentTime = from || 0; a.play().catch(function () {});
      if (dur) setTimeout(function () { a.pause(); }, dur * 1000);
      return a;
    }
  };
})();
