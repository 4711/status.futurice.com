!function(b){var d=function(a,c){this.$element=b(a);this.options=b.extend({},b.fn.button.defaults,c)};d.prototype={constructor:d,setState:function(a){var c=this.$element,b=c.data(),d=c.is("input")?"val":"html",a=a+"Text";b.resetText||c.data("resetText",c[d]());c[d](b[a]||this.options[a]);setTimeout(function(){"loadingText"==a?c.addClass("disabled").attr("disabled","disabled"):c.removeClass("disabled").removeAttr("disabled")},0)},toggle:function(){var a=this.$element.parent('[data-toggle="buttons-radio"]');
a&&a.find(".active").removeClass("active");this.$element.toggleClass("active")}};b.fn.button=function(a){return this.each(function(){var c=b(this),e=c.data("button"),f="object"==typeof a&&a;e||c.data("button",e=new d(this,f));"toggle"==a?e.toggle():a&&e.setState(a)})};b.fn.button.defaults={loadingText:"loading..."};b.fn.button.Constructor=d;b(function(){b("body").on("click.button.data-api","[data-toggle^=button]",function(a){a=b(a.target);a.hasClass("btn")||(a=a.closest(".btn"));a.button("toggle")})})}(window.jQuery);