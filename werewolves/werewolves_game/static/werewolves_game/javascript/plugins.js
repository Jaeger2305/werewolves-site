/***********************************************************************************************************************
* Plugins and snippets
***********************************************************************************************************************/
// credit to adamb http://stackoverflow.com/a/13866517/2276412
// makes a span editable on double click
$.fn.extend({
    editable: function () {
        var that = this,
            $edittextbox = $('<input type="text"></input>').css('min-width', that.width()),
            submitChanges = function () {
                that.html($edittextbox.val());
                that.show();
                that.trigger('editsubmit', [that.html()]);
                $(document).off('click', submitChanges);
                $edittextbox.detach();
            },
            tempVal;
        $edittextbox.click(function (event) {
            event.stopPropagation();
        });

        that.dblclick(function (e) {
            tempVal = that.html();
            $edittextbox.val(tempVal).insertBefore(that).off("keypress").on('keypress', function (e) {
                if ($(this).val() !== '') {
                    var code = (e.keyCode ? e.keyCode : e.which);
                    if (code == 13) {
                        submitChanges();
                    }
                }
            });
            that.hide();
            $(document).one("click", submitChanges);
        });
        return that;
    }
});