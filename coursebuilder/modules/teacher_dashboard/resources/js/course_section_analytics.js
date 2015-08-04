/**
 * This file contains the classes to manage Student Detail Mapping widgets.
 *  Modified version of the skill_tagging_lib.js
 */

var STUDENT_DETAIL_API_VERSION = '1';
var ESC_KEY = 27;
var MAX_STUDENT_DETAIL_REQUEST_SIZE = 10;

/*********************** Start Dependencies ***********************************/
// The following symols are required to be defined in the global scope:
//   cbShowMsg, cbShowMsgAutoHide
var showMsg = cbShowMsg;
var showMsgAutoHide = cbShowMsgAutoHide;
/************************ End Dependencies ************************************/

function parseAjaxResponse(s) {
  // XSSI prefix. Must be kept in sync with models/transforms.py.
  var xssiPrefix = ")]}'";
  return JSON.parse(s.replace(xssiPrefix, ''));
}

/**
 * InputEx adds a JSON prettifier to Array and Object. This works fine for
 * InputEx code but breaks some library code (e.g., jQuery.ajax). Use this
 * to wrap a function which should be called with the InputEx extras turned
 * off.
 *
 * @param f {function} A zero-args function executed with prettifier removed.
 */
function withInputExFunctionsRemoved(f) {
  var oldArrayToPrettyJsonString = Array.prototype.toPrettyJSONString;
  var oldObjectToPrettyJsonString = Object.prototype.toPrettyJSONString;
  delete Array.prototype.toPrettyJSONString;
  delete Object.prototype.toPrettyJSONString;

  try {
    f();
  } finally {
    if (oldArrayToPrettyJsonString !== undefined) {
      Array.prototype.toPrettyJSONString = oldArrayToPrettyJsonString;
    }
    if (oldObjectToPrettyJsonString !== undefined) {
      Object.prototype.toPrettyJSONString = oldObjectToPrettyJsonString;
    }
  }
}

/**
 * A student detail table builder.
 *
 * @class
 */
function StudentDetailTable(unitList) {
  this._unitList = unitList;
}

StudentDetailTable.prototype = {
  _buildRow: function(unit) {
    var tr = $('<tr class="row"></tr>');

    // add unit/lesson name
    var td = $(
        '<td class="unit">' +
        '  <span class="unit-name"></span>' +
        '</td>'
    );
    td.find('.unit-name').text(unit.name);
    tr.append(td);

    // add score
    var td = $(
        '<td class="score">' +
        '  <span class="unit-score"></span> ' +
        '</td>'
    );

    td.find('.unit-score').text(unit.score);
    tr.append(td);

    return tr;
  },

  _unitsCount: function() {
    var that = this;
    return Object.keys(that._unitList._unitLookupByIdTable).length;
  },

  _buildHeader: function() {
    var that = this;
    var thead = $(
      '<thead>' +
      '  <tr>' +
      '    <th class="unit">Unit <span class="unit-count"></span></th>' +
      '    <th class="score">Year</th>' +
      '  </tr>' +
      '</thead>'
    );
    thead.find('.unit-count').text('(' + that._unitsCount() + ')')
    return thead;
  },

  _buildBody: function() {
    var that = this;
    var tbody = $('<tbody></tbody>');

    var i = 0;
    that._unitList.eachUnit(function(unit) {
      var row = that._buildRow(unit);
      row.addClass( i++ % 2 == 0 ? 'even' : 'odd');
      tbody.append(row);
    });

    return tbody;
  },

  _refresh: function() {
    this._table.find('tbody').remove();
    this._table.append(this._buildBody());
  },

  buildTable: function() {
    var that = this;

    this._content = $(
      '<h3>Student Detail Table</h3>' +
      '<table class="units-table"></table>');

    this._table = this._content.filter('table.units-table');
    this._table.append(that._buildHeader());

    this._refresh();

    return this._content;
  }
};


/**
 * A proxy to load and work with a list of unit progress from the server. Each of the
 * units is an object with fields for ....
 *
 * @class
 */
function UnitList() {
  this._unitLookupByIdTable = {};
  this._studentName = '';
  this._studentEmail = '';
  this._xsrfToken = null;
}

UnitList.prototype = {
  /**
   * Load the unit list from the server.
   *
   * @method
   * @param callback {function} A zero-args callback which is called when the
   *     unit list has been loaded.
   */
  load: function(callback, param) {
    var that = this;
    $.ajax({
      type: 'GET',
      url: 'rest/modules/teacher_dashboard/student_progress',
      data: {'student': param},
      dataType: 'text',
      success: function(data) {
        that._onLoad(callback, data);
      },
      error: function(error) {
        showMsg('Can\'t load the student progress.');
      }
    });
  },

  /**
   * @param id {string}
   * @return {object} The unit with given id, or null if no match.
   */
  getUnitById: function(id) {
    return this._unitLookupByIdTable[id];
  },

  /**
   * @return {string} The student name
   */
   getStudentName: function () {
    return this._studentName;
   },

   /**
   * @return {string} The student email
   */
   getStudentEmail: function () {
    return this._studentEmail;
   },

  /**
   * Iterate over the unit in the list.
   *
   * @param callback {function} A function taking a unit as its arg.
   */
  eachUnit: function(callback) {
    for (var prop in this._unitLookupByIdTable) {
      if (this._unitLookupByIdTable.hasOwnProperty(prop)) {
        callback(this._unitLookupByIdTable[prop]);
      }
    }
  },

  _onLoad: function(callback, data) {
    data = parseAjaxResponse(data);
    if (data.status != 200) {
      showMsg('Unable to load student progress. Reload page and try again.');
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
    var unitList = payload['units'];
    _studentName = payload['student_name'];
    _studentEmail = payload['student_email'];

    this._unitLookupByIdTable = [];
    $.each(unitList, function() {
      that._unitLookupByIdTable[this.id] = this;
    });
  },
};


window.UnitList = UnitList;
window.StudentDetailTable = StudentDetailTable;