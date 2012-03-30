$(document).ready(function() {
 var onlinestatus = window.navigator.onLine;
 if (onlinestatus != false) {
   onlinestatus = true;
 }
 $.get("/frontpage_json.php", function(data) {
   for (var key in data.autofill) {
    if ($("#"+key) != null) {
     $("#"+key).html(data.autofill[key]);
    }
   }
 }, "json");
 if (!onlinestatus) {
  $("#notify-box").append("<div class='alert alert-block'><a class='close' data-dismiss='alert'>×</a><h4 class='alert-heading'>Running in offline mode</h4>Your browser is in offline mode, and this page comes from application cache. Data shown in these pages is not up-to-date or it might not ever load.</div>");
 }
});