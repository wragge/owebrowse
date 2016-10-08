$(function() {
  var $grid = $('#redactions').packery({
  // options...
    itemSelector: '.redaction',
    gutter: 1,
    stamp: '.stamp'
  });
  $grid.imagesLoaded().progress(function() {
    //$grid.css({ opacity: 1 });
    $grid.packery();
  });

  $grid.on( 'click', '.redaction', function( event ) {
    var $item = $( event.currentTarget );
    var isExpanded = $item.hasClass('is-expanded');
    $item.toggleClass('is-expanded');
    $('.redaction-caption', $item).toggle();
    $('.page-thumb', $item).toggle();
    if ( isExpanded ) {
      // if shrinking, shiftLayout
      $grid.packery();
    } else {
      // if expanding, fit it
      $grid.packery( 'fit', event.currentTarget );
    }
  });

  $('.page-thumb a').click(function() {
    event.preventDefault();
    window.open($(this).attr('href'), name='_blank');
    event.stopImmediatePropagation();
  });

//
//  var ias = $.ias({
//    container: "#redactions",
//    item: ".redaction",
//    pagination: "#pagination",
//    next: ".next",
//    delay: 400
//  });

//  ias.on('render', function(items) {
//      $(items).css({ opacity: 0 });
//  });

//  ias.on('rendered', function(items) {
//    $grid.imagesLoaded(function() {
//      $grid.packery('appended', items);
//      console.log(items);
//    });
//  });

});