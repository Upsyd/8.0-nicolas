$(document).ready(function () {
    if ($('div#cust_carousel').children().length > 0){
        $('div#products_grid').css("padding-top","20px");
    }
    $(".box-language a").each(function(){
        var href = $(this).attr('href').split('?')[0];
        if (href == window.location.pathname){
            $("#lang").text($(this).find('span').text());
        }
    });
    $('ul#left_main li').each(function(){
        if ($(this).find('ul.dropdown-submenu li').length == 0){
            $(this).find('div.level1').hide();
            $(this).find('a>b').removeClass('caret');
        }
    });
        
    $('#image img').attr('data-toggle', 'magnify');

    var $main_panel = $(".main_images"),
    $sub_panel = $(".sub_images"),
    flag = false,
    duration = 300;
    $main_panel
        .owlCarousel({
            items: 1,
            margin: 10,
            nav: true,
            dots: true
        })
        .on('changed.owl.carousel', function (e) {
            if (!flag) {
                flag = true;
                $sub_panel.trigger('to.owl.carousel', [e.item.index, duration, true]);
                flag = false;
            }
        });
    $sub_panel
        .owlCarousel({
            margin: 20,
            items: 6,
            nav: true,
            center: true,
            dots: true
        })
        .on('click', '.owl-item', function () {
            $main_panel.trigger('to.owl.carousel', [$(this).index(), duration, true]);
        })
        .on('changed.owl.carousel', function (e) {
            if (!flag) {
                flag = true;
                $main_panel.trigger('to.owl.carousel', [e.item.index, duration, true]);
                flag = false;
            }
        });
});
