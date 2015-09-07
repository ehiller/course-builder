
function parseAjaxResponse(s) {
  // XSSI prefix. Must be kept in sync with models/transforms.py.
  var xssiPrefix = ")]}'";
  return JSON.parse(s.replace(xssiPrefix, ''));
}

/**
 * A proxy to load and work with a list of activity cores for a student from the server. Each of the
 * scores is an object with fields TODO
 *
 * @class
 */

function ActivityScores() {
  this._activityScoresByStudentId = {};
  this._xsrfToken = null;
}

ActivityScores.prototype = {
   /**
   * Load the activity scores list from the server.
   *
   * @method
   * @param callback {function} A zero-args callback which is called when the
   *     activity score list has been loaded.
   * @param students {dict} a collection of students to get activity scores for
   */
  load: function(callback, students) {
    var that = this;

    var requestDict = {
      xsrf_token: that._xsrfToken,
      payload: JSON.stringify({
        'students': students
      })
    };

    var request = JSON.stringify(requestDict);

    $.ajax({
      type: 'GET',
      url: 'rest/modules/teacher_dashboard/activity_scores',
      data: {'request': request},
      dataType: 'text',
      success: function(data) {
        that._onLoad(callback, data);
      },
      error: function(error) {
        showMsg('Can\'t load the activity scores.');
      }
    });
  },
  _onLoad: function(callback, data) {
    data = parseAjaxResponse(data);
    if (data.status != 200) {
      showMsg('Unable to load activity scores. Reload page and try again.');
      return;
    }
    this._xsrfToken = data['xsrf_token'];
    var payload = JSON.parse(data['payload']);
    this._updateFromPayload(payload);

    if (callback) {
      callback();
    }
  },
  _updateFromPayload: function(payload) {
    var that = this;
    var activityScores = payload['scores'];

    this._activityScoresByStudentId = [];
    $.each(activityScores, function(key, value) {
      that._activityScoresByStudentId[key] = value;
    });
  }
}

//Expose functionality for global scope
window.ActivityScores = ActivityScores;
