$(document).ready(function() {
    $.tablesorter.addParser({ 
        // set a unique id 
        id: 'text-tagged', 
        is: function(s) { 
            // return false so this parser is not auto detected 
            return false; 
        }, 
        format: function(s) { 
            // format your data for normalization 
            return s.replace(/(<([^>]+)>)/ig,"");
        }, 
        // set type, either numeric or text 
        type: 'text' 
    }); 

    $.tablesorter.addParser({ 
        // set a unique id 
        id: 'digit-tagged', 
        is: function(s) { 
            // return false so this parser is not auto detected 
            return false; 
        }, 
        format: function(s) { 
            // format your data for normalization 
            return s.replace(/(<([^>]+)>)/ig,"");
        }, 
        // set type, either numeric or text 
        type: 'numeric' 
    }); 
     

    // Create the tablesorters, setting the column parsers explicictly
    // as they seem to be failing to auto detect
    $('#attribute-table').tablesorter({ 
        widgets: ["zebra"],  
        debug: true,
        headers: { 0:{sorter: 'text-tagged'},
                   1:{sorter: 'digit'},
                   2:{sorter: 'digit'},
                   3:{sorter: 'digit'},
                   4:{sorter: 'digit'},
                   5:{sorter: 'text'},
                   6:{sorter: 'digit'}
                 }
    });

    $('#item-table').tablesorter({ 
        widgets: ["zebra"],  
        debug: true,
        headers: { 0:{sorter: 'digit'},
                   1:{sorter: 'text'},
                   2:{sorter: 'digit'},
                   3:{sorter: 'text'},
                   4:{sorter: 'text'},
                   5:{sorter: 'digit'},
                   6:{sorter: 'digit'},
                   7:{sorter: 'text'}
                 }
    });

    $('#error-table').tablesorter({
        widgets: ["zebra"],  
        debug: true,
        headers: { 
            0:{sorter: 'digit-tagged'},
            1:{sorter: 'text'},
            2:{sorter: 'text'},
            3:{sorter: 'text'},
            4:{sorter: 'text'}
        }
    });

    $('.cluster-attributes-table').tablesorter({
        widgets: ["zebra"],  
        debug: true,
        headers: { 
            0:{sorter: 'text'},
            1:{sorter: 'digit'},
            2:{sorter: 'digit'},
            3:{sorter: 'digit'}
        }
    });

    $('.cluster-items-table').tablesorter({
        widgets: ["zebra"],  
        debug: true,
        headers: { 
            0:{sorter: 'digit'},
            1:{sorter: 'text'},
            2:{sorter: 'digit'},
            3:{sorter: 'text'}
        }
    });

    $('.attribute-list').tablesorter({
        widgets: ["zebra"],  
        debug: true,
        headers: { 
            0:{sorter: 'text-tagged'},
            1:{sorter: 'digit'},
            2:{sorter: 'digit'},
            3:{sorter: 'digit'}
        }
    });

    // Hide hide things with tablesorters that need to start hidden.
    // We do this because tablesorter doesn't seem to completely
    // initialize for elements with display:none.
    $('.cluster-items').hide();
    $('.cluster-attributes').hide();
    $('.cluster-list').hide();

    $('#attribute-table')
        .tablesorterFilter({filterContainer: $("#attribute-filter"),
                            filterClearContainer: $("#attribute-filter-clear"),
                            filterColumns: [0],
                            filterCaseSensitive: false});

    $('#row-count').html($('#item-table tbody').find('tr').length + ' items');

    $('#item-table')
        .tablesorterFilter({filterContainer: $("#id-filter"),
                            filterClearContainer: $("#id-filter-clear"),
                            filterColumns: [0],
                            filterCaseSensitive: false},
                           {filterContainer: $("#profile-filter"),
                            filterClearContainer: $("#profile-filter-clear"),
                            filterColumns: [3],
                            filterCaseSensitive: false},
                           {filterContainer: $("#status-filter"),
                            filterClearContainer: $("#status-filter-clear"),
                            filterColumns: [4],
                            filterCaseSensitive: false,
                            filterFunction: function(x,y){return x==y}},
                           {filterContainer: $("#text-filter"),
                            filterClearContainer: $("#text-filter-clear"),
                            filterColumns: [7],
                            filterCaseSensitive: false},
                           {filterContainer: $("#attribute-filter"),
                            filterClearContainer: $("#attribute-filter-clear"),
                            filterColumns: [8],
                            filterCaseSensitive: false})
        .tablesorterPager({container: $("#item-pager")}); 
    
    // Handle a link to a specific attribute/item in the table. Assumes
    // that anything after the hash that is numeric is an item ID and
    // anything else is a attribute name.
    var hash = window.location.hash.substring(1);
	if (hash.length > 0) {
        if (window.location.pathname.indexOf('attributes') > 0) {
            $('#'+hash).addClass('highlight');
        } else if (window.location.pathname.indexOf('items') > 0) {
            if ($.isNumeric(hash)) {
                $('#id-filter').val(hash).trigger('keyup');
            } else {
                $('#attribute-filter').val(hash).trigger('keyup');
            }
        }
	}

    $('.cluster-button').click(function(event) {
        $(event.target).closest('.cluster-category').find('.cluster-list').toggle(300);
    });

    $('.toggle-cluster-info').click(function(event) {
        var button = $(this);
        button.closest('.cluster').find('.cluster-items').toggle();
        button.closest('.cluster').find('.cluster-attributes').toggle();
        button.toggleClass('active');
    });

    // hovering over attribute in a cluster highlights items that contain the attribute
    $('.cluster .attribute').mouseover(function(event) {
        var attribute = $(this);
        var attributeName = attribute.find('a').html();
        var cluster = attribute.closest('.cluster'); 
        cluster.find('.item-row, .attribute').removeClass('highlight');
        cluster.find('.'+attributeName.replace('*','\\*')).addClass('highlight');
    });

    $('#toggle-help').click(function(event) {
        $('#help-content').slideToggle();
    });

    $('body').click(function(event) {
        $('#help-content').slideUp();
    });

    $('#help-box').click(function(event) {
        event.stopPropagation();
    });

});

