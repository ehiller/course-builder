/**
 * An activity scores table builder.
 *
 * @class
 */
function ActivityTable(activityScores) {
  this._activityScores = activityScores;
}

ActivityTable.prototype = {
  _buildRow: function(sequence, question) {

    var tr = $('<tr class="row"></tr>');

    // add question number
    var td = $(
        '<td class="question-info">' +
        '  Question ' + ++sequence +
        '</td>'
    );
    tr.append(td);

    // add choices
    $.each(question, function (key, choice) {
      var td = $(
        '<td class="choice-info-' + key + '">' +
          choice.count +
        '</td>'
      );
      tr.append(td);
    });

    return tr;
  },

  _buildHeader: function() {
    var numOfColumns = 0;
    $.each(this._activityScores, function (key, question) {
      if (numOfColumns === 0 || question.length > numOfColumns) {
        numOfColumns = question.length;
      }
    });

    var thead = $(
      '<thead>' +
      '  <tr>' +
      '    <th></th>' +
      '  </tr>' +
      '</thead>'
    );

    for (var i = 1; i <= numOfColumns; i++) {
      $(thead).find('tr').append('<th> Choice ' + i + '</th>');
    }

    return thead;
  },

  _buildBody: function() {
    var that = this;
    var tbody = $('<tbody></tbody>');

    var i = 0;
    $.each(that._activityScores, function (key, question) {
      var row = that._buildRow(key, question);
      row.addClass( i++ % 2 == 0 ? 'even' : 'odd');
      tbody.append(row);
    });

    return tbody;
  },

  _refresh: function() {
    this._table.find('tbody').remove();
    this._table.append(this._buildBody());
  },

  buildTable: function(unitId, lessonId) {
    var that = this;

    this._content = $(
      '<div class="info" style="margin: 10px;">' +
      '<h3>Question Scores for Unit ' + unitId + ', Lesson ' + lessonId + '</h3>' +
      '<table class="questions-table"></table>');

    this._table = this._content.find('.questions-table');
    this._table.append(that._buildHeader());

    this._refresh();

    return this._content;
  }
};

function retrieveLessonScores(scores, unitId, lessonId) {
  var lessonScores = {};

  $.each(scores, function (studentId, units) {
    var questions = units[unitId][lessonId];
    $.each(questions, function (sequence, question) {
      if (!lessonScores[sequence]) {
        $.each(question[11], function (key, value) {
          value.count = 0;
        });
        lessonScores[sequence] = question[11];
      }
      $.each(question[6], function (key, value) {
        if (question[4] === 'SaQuestion') {
          lessonScores[sequence][0].count += question[8];
          return;
        }
        else {
          lessonScores[sequence][value].count += 1;
        }
      });
    });
  });

  return lessonScores;
}


window.retrieveLessonScores = retrieveLessonScores;
window.ActivityTable = ActivityTable;