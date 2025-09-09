window.dash_clientside = Object.assign({}, window.dash_clientside, {
  guards: {
    checkToken: function(pathname){
      if (pathname !== "/login") {
        const t = localStorage.getItem("token") || sessionStorage.getItem("token");
        if (!t) { location.replace("/login"); }  // ← replace evita volver con back
      }
      return "";
    },
    saveToken: function(token){
      if (token) { localStorage.setItem("token", token); }
      return "";
    },
    doLogout: function(n){
      if (n){
        try { localStorage.removeItem("token"); } catch(e){}
        try { sessionStorage.removeItem("token"); } catch(e){}
        location.replace("/login");               // ← reemplaza historial
      }
      return "";
    }
  }
});

// Si el navegador restaura desde bfcache (al “back”), vuelve a checar:
window.addEventListener("pageshow", function(){
  const t = localStorage.getItem("token") || sessionStorage.getItem("token");
  if (!t && location.pathname !== "/login") location.replace("/login");
});
