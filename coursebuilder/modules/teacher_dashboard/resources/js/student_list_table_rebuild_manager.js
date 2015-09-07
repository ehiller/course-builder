

/**
 * functions to rebuild completion column based off of selected unit
 */
function rebuildCompletionColumn(students, unitSelect, lessonSelect) {
    var unitId = $(unitSelect).val();
    var lessonId = $(lessonSelect).val();
    $('.student-list-table > tbody > tr').each(function(index, value) {
        var completionValue;
        var lessonCompletionValue;
        var studentId = $(this).find('.student-id').val();

        if (unitId != 'course_completion') {
            completionValue = students[studentId].unit_completion[unitId] * 100;
            for (var i = 0; i < students[studentId].detailed_course_completion.length; i++) {
                var unit_detail = students[studentId].detailed_course_completion[i];
                if (unit_detail.unit_id == unitId) {
                    for (var j = 0; j < unit_detail.lessons.length; j++) {
                        if (unit_detail.lessons[j].lesson_id == lessonId) {
                            lessonCompletionValue = ( unit_detail.lessons[j].completion / 2 ) * 100;
                        }
                    }
                }
            }
        }
        else {
            completionValue = students[studentId].course_completion;
            lessonCompletionValue = 'N/A';
        }

        $(this).find('.student-progress').val(completionValue / 100);
        $(this).find('.student-progress').append('<div class="progress-bar">' +
            '<span style="width:' + completionValue / 100 + '%;">Progress: ' + completionValue + '%</span>' +
            '</div>');
        $(this).find('.student-completion-value').text(completionValue + '%');

        if (lessonCompletionValue == 'N/A') {
            $(this).find('.student-lesson-completion').text(lessonCompletionValue);
        }
        else {
            $(this).find('.student-lesson-completion').text(lessonCompletionValue + '%');
        }
    });
}

/**
 * Adding function to global scope for use in section list view
 */
window.RebuildCompletionColumn = rebuildCompletionColumn;