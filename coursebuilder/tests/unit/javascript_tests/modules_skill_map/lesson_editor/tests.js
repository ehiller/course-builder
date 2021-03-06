// Variables required in global scope
var cbShowMsg, cbShowMsgAutoHide;

function MockSkillList(list, locationList) {
  this.idCounter = 0;
  this.list = list || [];
  this.locationList = locationList;
}
MockSkillList.prototype = {
  getSkillById: function(skillId) {
    for (var i = 0; i < this.list.length; i++) {
      if (this.list[i].id == skillId) {
        return this.list[i];
      }
    }
    return null;
  },
  eachSkill: function(callback) {
    $.each(this.list, function() {
      callback(this);
    });
  },
  eachPrerequisite: function(skill, callback) {
    for (var i = 0; i < skill.prerequisite_ids.length; i++) {
      var prereq = this.getSkillById(skill.prerequisite_ids[i]);
      if (prereq) {
        callback(prereq);
      }
    }
  },
  createOrUpdateSkill: function(callback, name, description, prerequisiteIds,
      locationKeys, skillId) {
    var that = this;
    if (! skillId) {
      skillId = 'new-skill-' + (this.idCounter++);
    }
    locations = [];
    if (locationKeys){
      $.each(locationKeys, function() {
        locations.push(that.locationList.getByKey(this));
      })
    }
    var skill = {
      id: skillId,
      name: name,
      description: description,
      prerequisite_ids: prerequisiteIds,
      locations: locations
    };
    this.list.push(skill);
    callback(skill, 'OK');
  }
};

function MockLocationList(list) {
  this.list = list || [];
}
MockLocationList.prototype = {
  each: function(callback) {
    $.each(this.list, function() {
      callback(this);
    });
  },
  getByKey: function(key) {
    for (var i = 0; i < this.list.length; i++) {
      if (this.list[i].key == key) {
        return this.list[i];
      }
    }
    return null;
  }
}

describe('The skill tagging library', function() {

  beforeEach(function() {
    showMsg = jasmine.createSpy('showMsg');
    showMsgAutoHide = jasmine.createSpy('showMsgAutoHide');

    jasmine.getFixtures().fixturesPath = 'base/';
    loadFixtures('tests/unit/javascript_tests/modules_skill_map/' +
        'lesson_editor/fixture.html');
  });

  afterEach(function() {
    delete SKILL_API_VERSION;
    delete parseAjaxResponse;
    delete showMsg;
    delete showMsgAutoHide;

    // Tidy up any leftover lightboxes
    $(document.body).empty();
  });

  describe('SkillList', function() {
    var SKILL_LIST_REST_RESPONSE = {
      status: 200,
      xsrf_token: 'valid_xsrf_token',
      payload: JSON.stringify({
        skill_list: [
          {
            id: 's111',
            name: 'rock climbing',
            description: 'can climb rocks',
            prerequisite_ids: []
          },
          {
            id: 's222',
            name: 'ice skating',
            description: 'can skate on ice',
            prerequisite_ids: []
          }
        ],
        diagnosis: {
          cycles: [],
          singletons: [],
          long_chains: []
        }
      })
    };

    beforeEach(function() {
      this.skillList = new SkillList();
      this.callback = jasmine.createSpy('callback');
      spyOn($, 'ajax');
    });

    describe('loading the skill map', function() {
      it('GETs from the skill_list REST service', function() {
        this.skillList.load(this.callback);
        expect($.ajax).toHaveBeenCalled();
        var arg = $.ajax.calls[0].args[0];
        expect(arg.type).toEqual('GET');
        expect(arg.url).toEqual('rest/modules/skill_map/skill');
        expect(arg.dataType).toEqual('text');
      });
      it('displays an error if the status is not 200', function() {
        this.skillList.load(this.callback);
        $.ajax.calls[0].args[0].success(JSON.stringify({status: 400}));
        expect(showMsg).toHaveBeenCalled();
        expect(showMsg.calls[0].args[0]).toMatch(/^Unable to load skill map./);
      });
      it('loads a valid skill map', function() {
        this.skillList.load(this.callback);
        $.ajax.calls[0].args[0].success(JSON.stringify(SKILL_LIST_REST_RESPONSE));
        expect(this.callback).toHaveBeenCalled();
        expect(this.skillList.getSkillById('s111')).toEqual({
          id: 's111', name: 'rock climbing', description: 'can climb rocks',
          prerequisite_ids: []});
        expect(this.skillList.getSkillById('s222')).toEqual({
          id: 's222', name: 'ice skating', description: 'can skate on ice',
          prerequisite_ids: []});
      });
    });

    describe('adding to the skill map', function() {
      it('PUTs to the skill REST service', function() {
        this.skillList.createOrUpdateSkill(
            this.callback, 'ice skating', 'can skate');
        expect($.ajax).toHaveBeenCalled();
        var arg = $.ajax.calls[0].args[0];
        expect(arg.type).toEqual('PUT');
        expect(arg.url).toEqual('rest/modules/skill_map/skill');
        var request = JSON.parse(arg.data.request);
        var payload = JSON.parse(request.payload);
        expect(payload).toEqual({
          version: '1',
          name: 'ice skating',
          description: 'can skate',
          prerequisites: [],
          locations: []
        });
      });
      it('displays an error if the status is not 200', function() {
        this.skillList.createOrUpdateSkill(
            this.callback, 'ice skating', 'can skate');
        $.ajax.calls[0].args[0].success(JSON.stringify(
            {status: 400, message: 'Server error'}));
        expect(showMsg).toHaveBeenCalled();
        expect(showMsg.calls[0].args[0]).toEqual('Server error');
      });
      it('inserts the skill with key, and issues callback after save', function() {
        this.skillList.createOrUpdateSkill(
            this.callback, 'ice skating', 'can skate');
        var payload = {
          status: 200,
          message: 'OK',
          payload: JSON.stringify({
            key: 'skill001',
            skill: {
              id: 'skill001',
              name: 'ice skating',
              description: 'can skate',
              prerequisite_ids: []
            },
            skill_list: [],
            diagnosis: []
          })
        };
        $.ajax.calls[0].args[0].success(JSON.stringify(payload));
        expect(this.callback).toHaveBeenCalled();
        expect(this.callback.calls[0].args[0]).toEqual({
          id: 'skill001',
          name: 'ice skating',
          description: 'can skate',
          prerequisite_ids: []
        });
        expect(this.callback.calls[0].args[1]).toEqual('OK');
      });
    });

    describe('deleting a skill', function() {
      it ('DELETEs the skill with the REST service', function() {
        // Load the sample skill map
        this.skillList.load(this.callback);
        $.ajax.calls[0].args[0]
            .success(JSON.stringify(SKILL_LIST_REST_RESPONSE));

        var retval = this.skillList.deleteSkill(this.callback, 's111');

        var arg = $.ajax.calls[1].args[0];
        expect(arg.type).toEqual('DELETE');
        expect(arg.url).toEqual('rest/modules/skill_map/skill' +
            '?xsrf_token=valid_xsrf_token&key=s111');
        expect(retval).toBe(true);
      });
      it('returns FALSE when asked to delete non-existent skill', function() {
        expect(this.skillList.deleteSkill(this.callback, 's111')).toBe(false);
      });
      it ('displays an error message if the status is not 200', function() {
        // Load the sample skill map
        this.skillList.load(this.callback);
        $.ajax.calls[0].args[0]
            .success(JSON.stringify(SKILL_LIST_REST_RESPONSE));

        this.skillList.deleteSkill(this.callback, 's111');
        $.ajax.calls[1].args[0].success(JSON.stringify(
            {status: 400, message: 'Server error'}));
        expect(showMsg).toHaveBeenCalled();
        expect(showMsg.calls[0].args[0]).toEqual('Server error');
      });
      it ('calls the callback', function() {
        // Load the sample skill map
        this.skillList.load(this.callback);
        $.ajax.calls[0].args[0]
            .success(JSON.stringify(SKILL_LIST_REST_RESPONSE));

        this.skillList.deleteSkill(this.callback, 's111');
        var payload = {
          status: 200,
          message: 'OK',
          payload: JSON.stringify({
            skill_list: [],
            diagnosis: []
          })
        };
        $.ajax.calls[1].args[0].success(JSON.stringify(payload));
        expect(this.callback.calls[1].args[0]).toEqual('success');
        expect(this.callback.calls[1].args[1]).toEqual('OK');
      });
    });
  });

  describe('Lighbox', function() {
    beforeEach(function() {
      this.root = $('#root');
      this.lightbox = new Lightbox();
    });

    it('adds hidden lighbox to the DOM when bound', function() {
      expect(this.root.find('div.lightbox').length).toEqual(0);
      this.lightbox.bindTo(this.root);
      expect(this.root.find('div.lightbox').length).toEqual(1);
      expect(this.root.find('div.lightbox')).toBeHidden();
    });

    it('becomes visible when shown', function() {
      this.lightbox.bindTo(this.root).show();
      expect(this.root.find('div.lightbox')).toBeVisible();
    });

    it('is removed when closed', function() {
      this.lightbox.bindTo(this.root).show().close();
      expect(this.root.find('div.lightbox').length).toEqual(0);
    });
  });

  describe('ItemSelector', function() {

    beforeEach(function() {
      this.root = $('#root');
      this.callback = jasmine.createSpy('callback');
      this.selector = new ItemSelector(this.callback);
      this.root.append(this.selector.element());
      this.selector.add('s1', 'ice skating');
      this.selector.add('s2', 'rock climbing');
    });

    it('is closed initially', function() {
      expect($('div.selector')).toBeHidden();
    });

    it('opens the selector when the add button is clicked', function() {
      $('button.add').click();
      expect($('div.selector')).toBeVisible();
    });

    it('lists the items in the selector', function() {
      expect($('ol.item-list li span').length).toBe(2);
      expect($('ol.item-list li span').eq(0).text()).toBe('ice skating');
      expect($('ol.item-list li span').eq(1).text()).toBe('rock climbing');
    });

    it('filters the list when text is entered', function() {
      $('button.add').click();
      $('input.search').val('ice').keyup();
      expect($('ol.item-list li:visible').length).toBe(1);
      expect($('ol.item-list li:visible').text()).toBe('ice skating');
    });

    it('disables the OK button when no items are selected', function() {
      $('button.add').click();
      expect($('button.select')).toBeDisabled();
    });

    it('enables the OK button when items are selected', function() {
      $('button.add').click();
      $('input[type=checkbox]:first').click();
      expect($('button.select')).not.toBeDisabled();
    });

    it('returns the selected item ids to the callback', function() {
      $('button.add').click();
      $('input[type=checkbox]:first').click();
      $('button.select').click();
      expect(this.callback).toHaveBeenCalled();
      expect(this.callback.calls[0].args[0].length).toBe(1);
      expect(this.callback.calls[0].args[0][0]).toBe('s1');
    });

    it('is disabled when empty', function() {
      this.root = $('#root').empty();
      this.callback = jasmine.createSpy('callback');
      this.selector = new ItemSelector(this.callback);
      this.root.append(this.selector.element());

      expect($('button.add').prop('disabled')).toBe(true);
      this.selector.add('s1', 'ice skating');
      expect($('button.add').prop('disabled')).toBe(false);
      this.selector.clear();
      expect($('button.add').prop('disabled')).toBe(true);
    });
  });

  describe('EditSkillPopup', function() {
    beforeEach(function() {
      this.callback = jasmine.createSpy('callback');
      this.locationList = new MockLocationList([
      {
        key: 'loc-1',
        label: '1.1',
        href: '/unit?lesson=1',
        edit_href: '/edit?lesson=1',
        lesson: 'Lesson 1',
        unit: 'Unit 1',
        sort_key: 0
      }
      ]);
      this.skillList = new MockSkillList([
        {
          id: 's111',
          name: 'rock climbing',
          description: 'can climb rocks',
          prerequisite_ids: [],
          locations: []
        },
        {
          id: 's222',
          name: 'ice skating',
          description: 'can skate on ice',
          prerequisite_ids: [],
          locations: []
        }
      ], this.locationList);
    });

    it('is hidden until opened', function() {
      var popup = new EditSkillPopup(this.skillList);
      expect($('div.edit-skill-popup').length).toBe(0);

      popup.open(this.callback);
      expect($('div.edit-skill-popup').length).toBe(1);
    });

    it('can create a new skill', function() {
      var popup = new EditSkillPopup(this.skillList);
      popup.open(this.callback);

      var popupDiv = $('div.edit-skill-popup');
      expect(popupDiv.find('.title').text()).toBe('Create New Skill');

      // Set name and description
      popupDiv.find('.skill-name').val('new-skill');
      popupDiv.find('.skill-description').val('new-skill-description');

      // Save
      popupDiv.find('.new-skill-save-button').click();

      var expectedSkill = {
        id: 'new-skill-0',
        name: 'new-skill',
        description: 'new-skill-description',
        prerequisite_ids: [],
        locations: []
      };

      expect(this.callback.calls.length).toBe(1);
      expect(this.callback.calls[0].args[0]).toEqual(expectedSkill);
      expect(this.skillList.list.length).toBe(3);
      expect(this.skillList.list[2]).toEqual(expectedSkill);
    });

    it('can update an existing skill', function() {
      var popup = new EditSkillPopup(this.skillList, null, 's111');
      popup.open(this.callback);

      var popupDiv = $('div.edit-skill-popup');
      expect(popupDiv.find('.title').text()).toBe('Edit Skill');

      // Confirm old values
      expect(popupDiv.find('.skill-name').val()).toBe('rock climbing');
      expect(popupDiv.find('.skill-description').val()).toBe('can climb rocks');

      // Set name and description
      popupDiv.find('.skill-name').val('new-skill');
      popupDiv.find('.skill-description').val('new-skill-description');

      // Save
      popupDiv.find('.new-skill-save-button').click();

      var expectedSkill = {
        id: 's111',
        name: 'new-skill',
        description: 'new-skill-description',
        prerequisite_ids: [],
        locations: []
      };

      expect(this.callback.calls.length).toBe(1);
      expect(this.callback.calls[0].args[0]).toEqual(expectedSkill);
      expect(this.skillList.list.length).toBe(3);
      expect(this.skillList.list[2]).toEqual(expectedSkill);
    });

    it('can set prerequisites', function() {
      var popup = new EditSkillPopup(this.skillList, null, 's111');
      popup.open(this.callback);

      var popupDiv = $('div.edit-skill-popup');
      var prerequisites = popupDiv.find('.skill-prerequisites');

      // Expect the popup is not displaying any prerequisites yet
      expect(prerequisites.find('ol.skill-display-root li').length).toBe(0);

      // Click the "Add Skill" button in the "Prerequisites" section
      expect(prerequisites.find('button.add').text()).toBe('+ Add Skill');
      popupDiv.find('.skill-prerequisites button.add').click();
      expect(prerequisites.find('.item-selector-root .selector')).toBeVisible();

      // Click the selector to select skill "s122" ("Ice Skating")
      var items = prerequisites
          .find('.item-selector-root .selector .item-list li');
      expect($(items[1]).text()).toBe('ice skating');
      $(items[1]).find('input').click();
      expect($(items[1]).find('input').length).toBe(1);
      prerequisites.find('.item-selector-root .selector button.select')
          .click();

      // Expect the popup is now displaying the selected prerequisite
      expect(prerequisites.find('ol.skill-display-root li').length).toBe(1);
      expect(prerequisites.find('ol.skill-display-root li').text())
          .toBe('ice skatingx'); // (The 'x' is the button to remove the skill)

      // Save
      popupDiv.find('.new-skill-save-button').click();

      // Expect skill "s122 ("Ice Skating") as a prerequisite
      var expectedSkill = {
        id: 's111',
        name: 'rock climbing',
        description: 'can climb rocks',
        prerequisite_ids: ['s222'],
        locations: []
      };

      expect(this.callback.calls.length).toBe(1);
      expect(this.callback.calls[0].args[0]).toEqual(expectedSkill);
      expect(this.skillList.list.length).toBe(3);
      expect(this.skillList.list[2]).toEqual(expectedSkill);
    });

    it('can set lessons', function() {
      var popup = new EditSkillPopup(this.skillList, this.locationList, 's111');
      popup.open(this.callback);

      var popupDiv = $('div.edit-skill-popup');

      // Expect the popup is not displaying any lessons yet
      expect(popupDiv.find('ol.location-display-root li').length).toBe(0);

      // Click the "Add Lesson" button in the "Lessons" section
      expect(popupDiv.find('.lessons button.add').text()).toBe('+ Add Lesson');
      popupDiv.find('.lessons button.add').click();
      expect(popupDiv.find('.lessons .item-selector-root .selector'))
          .toBeVisible();

      // Click the selector to select "Lesson 1"
      var items = popupDiv.find(
          '.lessons .item-selector-root .selector .item-list li');
      expect($(items[0]).text()).toBe('1.1 Lesson 1');
      $(items[0]).find('input').click();
      expect($(items[0]).find('input').length).toBe(1);
      popupDiv.find('.lessons .item-selector-root .selector button.select')
          .click();

      // Expect the popup is now displaying the selected lesson
      expect(popupDiv.find('ol.location-display-root li').length).toBe(1);
      expect(popupDiv.find('ol.location-display-root li').text())
        .toBe('1.1 Lesson 1x'); // (The 'x' is the button to remove the skill)

      // Save
      popupDiv.find('.new-skill-save-button').click();

      // Expect skill "Lesson 1" to be tagged
      var expectedSkill = {
        id: 's111',
        name: 'rock climbing',
        description: 'can climb rocks',
        prerequisite_ids: [],
        locations: [
          {
            key: 'loc-1',
            label: '1.1',
            href: '/unit?lesson=1',
            edit_href: '/edit?lesson=1',
            lesson: 'Lesson 1',
            unit: 'Unit 1',
            sort_key: 0
          }
        ]
      };

      expect(this.callback.calls.length).toBe(1);
      expect(this.callback.calls[0].args[0]).toEqual(expectedSkill);
      expect(this.skillList.list.length).toBe(3);
      expect(this.skillList.list[2]).toEqual(expectedSkill);
    });

    it('can omit the Lesson selector', function() {
      // Open with location list absent
      var popup = new EditSkillPopup(this.skillList, null, 's111');
      popup.open(this.callback);
      // Expect the lesson choser to be hidden
      expect($('div.edit-skill-popup .form-row.location-row')).toBeHidden();
    });

    it('can show the Lesson selector', function() {
      // Open with location list present
      var popup = new EditSkillPopup(this.skillList, this.locationList, 's111');
      popup.open(this.callback);
      // Expect the lesson choser to be visible
      expect($('div.edit-skill-popup .form-row.location-row')).toBeVisible();
    });
  });
});
