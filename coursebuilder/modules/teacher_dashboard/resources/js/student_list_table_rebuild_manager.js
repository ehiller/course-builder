

/**
 * functions to rebuild completion column based off of selected unit
 */
function rebuildCompletionColumn(students, unitSelect, lessonSelect) {
    var unitId = $(unitSelect).val();
    var lessonId = $(lessonSelect).val();
    $('.student-list-table > tbody > tr').each(function(index, value) {
        var completionValue;
        var lessonCompletionValue;
        var lessonScore;
        var studentId = $(this).find('.student-id').val();

        if (unitId != 'course_completion') {
            completionValue = students[studentId].unit_completion[unitId] * 100;
            for (var i = 0; i < students[studentId].detailed_course_completion.length; i++) {
                var unit_detail = students[studentId].detailed_course_completion[i];
                if (unit_detail.unit_id == unitId) {
                    for (var j = 0; j < unit_detail.lessons.length; j++) {
                        if (unit_detail.lessons[j].lesson_id == lessonId) {
                            lessonCompletionValue = ( unit_detail.lessons[j].completion / 2 ) * 100;
                            lessonScore = calculateLessonScore(studentId, unitId, lessonId, window.scores);
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
            $(this).find('.student-lesson-completion > .student-lesson-completion-percentage').text
            (lessonCompletionValue);
        }
        else {
            $(this).find('.student-lesson-completion > .student-lesson-completion-percentage').text(lessonCompletionValue + '%');
            if (lessonScore) {
                $(this).find('.student-lesson-completion > .student-lesson-completion-score').text(lessonScore.total +
                '/' + lessonScore.possible);
            }
        }
    });
}

/**
 * function to calculate a students scores for a lesson
 */
function calculateLessonScore(studentId, unitId, lessonId, scores) {

    studentScores = scores[studentId];
    var lessonScore = {
        possible: 0, total: 0
    };

    if (scores[studentId]) {
        if (scores[studentId][unitId]) {
            if (scores[studentId][unitId][lessonId]) {
                questions = scores[studentId][unitId][lessonId];

                $.each(questions, function (key, value) {
                    lessonScore.total += value[8];
                    lessonScore.possible += value[10];
                });
            }
        }
    }

    return lessonScore;
}

/**
 * Adding function to global scope for use in section list view
 */
window.RebuildCompletionColumn = rebuildCompletionColumn;