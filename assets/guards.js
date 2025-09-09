window.dash_clientside = Object.assign({}, window.dash_clientside, {
  guards: {
    checkToken: function(pathname){
      if (pathname !== "/login") {
        const t = window.localStorage.getItem("token");
        if (!t) { window.location.href = "/login"; }
      }
      return "";
    },
    saveToken: function(token){
      if (token) { localStorage.setItem("token", token); }
      return "";
    },
    doLogout: function(n){
      if (n){ localStorage.removeItem("token"); location.href="/login"; }
      return "";
    }
  }
});
