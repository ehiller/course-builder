__author__ = 'ehiller@css.edu'


# Module to support custom teacher views in CourseBuilder dashboard
# Views include:
#       Section Roster - list of students in section
#       Sections - list of sections for current user
#       Student Dashboard - view of a single student's performance in the course
#       Teacher Workspace - teacher registration and list of all registered teachers

import jinja2
import os

import appengine_config
import teacher_entity

from common import tags
from common import crypto

from models import custom_modules
from models import roles
from models import transforms
from models.models import Student

from controllers.utils import BaseRESTHandler

from common.resource import AbstractResourceHandler
from common import schema_fields

#since we are extending the dashboard, probably want to include dashboard stuff
from modules.dashboard import dashboard
from modules.dashboard import tabs

#Setup paths and directories for templates and resources
RESOURCES_PATH = '/modules/teacher_dashboard/resources'

TEMPLATES_DIR = os.path.join(
    appengine_config.BUNDLE_ROOT, 'modules', 'teacher_dashboard', 'templates')

#setup permissions that will be registered with the dashboard
ACCESS_ASSETS_PERMISSION = 'can_access_assets'
ACCESS_ASSETS_PERMISSION_DESCRIPTION = 'Can access the Assets Dashboard'

ACCESS_SETTINGS_PERMISSION = 'can_access_settings'
ACCESS_SETTINGS_PERMISSION_DESCRIPTION = 'Can access the Settings Dashboard'

ACCESS_ROLES_PERMISSION = 'can_access_roles'
ACCESS_ROLES_PERMISSION_DESCRIPTION = 'Can access the Roles Dashboard'

ACCESS_ANALYTICS_PERMISSION = 'can_access_analytics'
ACCESS_ANALYTICS_PERMISSION_DESCRIPTION = 'Can access the Analytics Dashboard'

ACCESS_SEARCH_PERMISSION = 'can_access_search'
ACCESS_SEARCH_PERMISSION_DESCRIPTION = 'Can access the Search Dashboard'

ACCESS_PEERREVIEW_PERMISSION = 'can_access_peer_review'
ACCESS_PEERREVIEW_PERMISSION_DESCRIPTION = 'Can access the Peer Review Dashboard'

ACCESS_SKILLMAP_PERMISSION = 'can_access_skill_map'
ACCESS_SKILLMAP_PERMISSION_DESCRIPTION = 'Can access the Skill Map Dashboard'

ACCESS_TEACHER_DASHBOARD_PERMISSION = 'can_access_teacher_dashboard'
ACCESS_TEACHER_DASHBOARD_PERMISSION_DESCRIPTION = 'Can access the Teacher Dashboard'

#setup custom module for, needs to be referenced later
custom_module = None


class TeacherHandler(dashboard.DashboardHandler):
    """Handler for everything under the Teacher tab in the CourseBuilder dashboard.

    Note:
        Inherits from the DashboardHandler, makes use of many of those functions to
        integrate with existing dashboard.

    Attributes:
        ACTION (str): Value used to handler navigation in the dashboard, top level label.
        DEFAULT_TAB (str): Default sub-navigation value.
        URL (str): Path to module from working directory.
        XSRF_TOKEN_NAME (str): Token used for xsrf security functions.

    """

    ACTION = 'teacher_dashboard'
    DEFAULT_TAB = 'sections'

    URL = '/modules/teacher_dashboard'

    XSRF_TOKEN_NAME = ''

    @classmethod
    def register_tabs(cls):
        """Handles registering all sub-navigation tabs"""

        def register_tab(key, label, handler, href=None):
            """Registers tab using the tab registry"""
            if href:
                target = '_blank'
            else:
                href = 'dashboard?action=teacher_dashboard&tab=%s' % key
                target = None

            tabs.Registry.register(
                cls.ACTION, key, label, contents=handler, href=href, target=target
            )

        register_tab('sections', 'Sections', TeacherHandler)
        register_tab('student_detail', 'Student Dashboard', TeacherHandler)
        register_tab('teacher_reg', 'Teacher Workspace', TeacherHandler)

    def get_teacher_dashboard(self):
        """Process navigation requests sent to teacher handler. Routers to appropriate function."""

        in_tab = self.request.get('tab') or self.DEFAULT_TAB
        tab_action = self.request.get('tab_action') or None #defined a secondary tab property so I can go load a
                                                            # separate view in the same tab

        if in_tab == 'sections':
            if tab_action == 'roster':
                return self.get_roster()
            else:
                return self.get_sections()
        elif in_tab == 'teacher_reg':
            return self.get_teacher_reg()
        elif in_tab == 'student_detail':
            return self.get_student_dashboard()

    def get_sections(self):
        """Renders Sections view. Javascript handles getting course sections and building the view"""
        main_content = self.get_template(
            'teacher_sections.html', [TEMPLATES_DIR]).render({})

        self.render_page({
            'page_title': self.format_title('Sections'),
            'main_content': jinja2.utils.Markup(main_content)})

    def get_student_dashboard(self):
        """Renders Student Dashboard view.

           Also gets ALL students in ALL course sections for the registered user to
           build a jQuery autocomplete dropdown on the view.
        """

        student_email = self.request.get('student') or None #email will be in the request if opened from student list
                                                            # view, otherwise it will be None

        #need to go through every course section for the current user and get all unique students
        students = []
        course_sections = teacher_entity.CourseSectionEntity.get_course_sections_for_user()
        for course_section in course_sections.values():
            for student_in_section in course_section.students.values():
                if not student_in_section in students:
                    students.append(student_in_section)

        #check to see if we have a student and if we need to get detailed progress
        student = None
        if student_email:
            student = Student.get_by_email(student_email)

        if (student):
            course = self.get_course()
            units = StudentProgressTracker.get_detailed_progress(student, course)
        else:
            units = None

        #render the template for the student dashboard view
        main_content = self.get_template(
            'student_detailed_progress.html', [TEMPLATES_DIR]).render(
                {
                    'units': units, #unit completion
                    'student': student, #course defined student object, need email and name
                    'students': students #list of students, names and emails, from a course section student list
                })

        #call DashboardHandler function to render the page
        self.render_page({
            'page_title': self.format_title('Student Dashboard'),
            'main_content': jinja2.utils.Markup(main_content)
        })


    def get_roster(self):
        """Renders the Roster view. Displays all students in a single course section

           Also allows user to add students to a course section
        """

        template_values = {}
        template_values['add_student_xsrf_token'] = crypto.XsrfTokenManager.create_xsrf_token(CourseSectionRestHandler.XSRF_TOKEN)

        #need list of units and lessons for select elements that determine which progress value to display
        #need a list of units, need the titles, unit ids, types
        units = self.get_course().get_units()
        units_filtered = filter(lambda x: x.type == 'U', units) #filter out assessments
        template_values['units'] = units_filtered

        #need to get lessons, but only for units that aren't assessments
        lessons = {}
        for unit in units_filtered:
            unit_lessons = self.get_course().get_lessons(unit.unit_id)
            unit_lessons_filtered = []
            for lesson in unit_lessons:
                unit_lessons_filtered.append({
                    'title': lesson.title,
                    'unit_id': lesson.unit_id,
                    'lesson_id': lesson.lesson_id
                })
            lessons[unit.unit_id] = unit_lessons_filtered
        template_values['lessons'] = transforms.dumps(lessons, {}) #passing in JSON to template so it can be used
                                                                    # in JavaScript

        course_section_id = self.request.get('section')

        course_section = teacher_entity.CourseSectionEntity.get_course_for_user(course_section_id)

        #need to get progress values for ALL students since we show completion for every student
        if course_section.students and len(course_section.students) > 0:
            for student in course_section.students.values():
                student['unit_completion'] = StudentProgressTracker.get_unit_completion(Student.get_by_email(student[
                    'email']), self.get_course())
                student['course_completion'] = StudentProgressTracker.get_overall_progress(Student.get_by_email(student[
                    'email']), self.get_course())
                student['detailed_course_completion'] = StudentProgressTracker.get_detailed_progress(
                    Student.get_by_email(student['email']), self.get_course())

        #passing in students as JSON so JavaScript can handle updating completion values easier
        template_values['students_json'] = transforms.dumps(course_section.students, {})

        if course_section:
            template_values['section'] = course_section

        #render student_list.html for Roster view
        main_content = self.get_template(
            'student_list.html', [TEMPLATES_DIR]).render(template_values)

        #DashboardHandler renders the page
        self.render_page({
            'page_title': self.format_title('Student List'),
            'main_content': jinja2.utils.Markup(main_content)})


    def get_teacher_reg(self):
        """Renders Teacher Workspace view. Displays form to add or update a teacher

           Also displays all registered teachers.
        """

        template_values = {}
        template_values['teacher_reg_xsrf_token'] = self.create_xsrf_token('teacher_reg')

        template_values['teachers'] = teacher_entity.Teacher.get_all_teachers_for_course()

        main_content = self.get_template(
            'teacher_registration.html', [TEMPLATES_DIR]).render(template_values)

        self.render_page({
            'page_title': self.format_title('Teacher Registration'),
            'main_content': jinja2.utils.Markup(main_content)})

    def post_teacher_reg(self):
        """Handles form submit for teacher registration"""

        #get values entered on form
        email = self.request.get('email').strip()
        school = self.request.get('school')

        #getting checkbox value is a little weird, might look different depending on browser
        active = self.request.get('active-teacher')
        if active == 'on' or len(active) > 0:
            active = True
        else:
            active = False

        teacher = teacher_entity.Teacher.get_by_email(email)

        #keep track of any errors we might want to pass back to the UI
        alerts = []

        #check to see if a teacher already exists
        if teacher:
            template_values = {}

            template_values['teacher_reg_xsrf_token'] = self.create_xsrf_token('teacher_reg')

            sections = {}

            #don't let the teacher be deactivated if they have active courses
            can_inactivate = True
            if active == False:
                if teacher.sections:
                    course_sections_decoded = transforms.loads(teacher.sections)

                    for course_section_key in course_sections_decoded:
                        course_section = teacher_entity.CourseSectionEntity(course_sections_decoded[course_section_key])
                        sections[course_section.section_id] = course_section

                    for section in sections.values():
                        if section.is_active:
                            can_inactivate = False

            #let user know if they can't deactivate, but only if they are trying to deactivate the teacher
            if not can_inactivate and not active:
                alerts.append('Cannot deactivate teacher. Teacher still has active courses')

            #go for the update if all is good
            if can_inactivate:
                teacher_entity.Teacher.update_teacher_for_user(email, school, active, '', alerts)

            #let user know all is well if save was successful
            if len(alerts) == 0:
                alerts.append('Teacher was successfully updated')

            #render teacher_registration.html for view, pass alerts in
            template_values['alert_messages'] = '\n'.join(alerts)
            main_content = self.get_template(
                'teacher_registration.html', [TEMPLATES_DIR]).render(template_values)

            #DashboardHandler renders the page
            self.render_page({
                'page_title': self.format_title('Teacher Dashboard'),
                'main_content': jinja2.utils.Markup(main_content)
                },
                'teacher_dashboard'
            )
        else:
            #go for it if teacher doesn't already exist
            teacher_entity.Teacher.add_new_teacher_for_user(email, school, '', alerts)

            template_values = {}

            template_values['alert_messages'] = '\n'.join(alerts)
            template_values['teacher_reg_xsrf_token'] = self.create_xsrf_token('teacher_reg')
            main_content = self.get_template(
                'teacher_registration.html', [TEMPLATES_DIR]).render(template_values)

            #DashboardHandler renders the page
            self.render_page({
                'page_title': self.format_title('Teacher Dashboard'),
                'main_content': jinja2.utils.Markup(main_content)
                },
                'teacher_dashboard'
            )

class StudentProgressTracker(object):
    """Gets student progress for a given course.

    Note:
        Gets progress at the unit, lesson, and course levels.

    """

    @classmethod
    def get_unit_completion(cls, student, course):
        """Gets completion progress for all units in a course for a student"""
        tracker = course.get_progress_tracker()

        return tracker.get_unit_percent_complete(student)

    @classmethod
    def get_overall_progress(cls, student, course):
        """Gets progress at the course level for a student"""
        tracker = course.get_progress_tracker()

        unit_completion = tracker.get_unit_percent_complete(student)

        course_completion = 0
        for unit_completion_value in unit_completion.values():
            course_completion += unit_completion_value

        #return percentages
        course_completion = (course_completion / len(unit_completion)) * 100

        return course_completion

    @classmethod
    def get_detailed_progress(cls, student, course, include_assessments = False):
        """Gets unit and lesson completion for in a course for a student"""
        units = []

        tracker = course.get_progress_tracker()

        progress = tracker.get_or_create_progress(student)
        unit_completion = tracker.get_unit_percent_complete(student)

        course_units = course.get_units()
        if not include_assessments:
            course_units = filter(lambda x: x.type == 'U', course_units)

        for unit in course_units:
            # Don't show assessments that are part of units.
            if course.get_parent_unit(unit.unit_id):
                continue

            if unit.unit_id in unit_completion:
                lessons = course.get_lessons(unit.unit_id)
                lesson_status = tracker.get_lesson_progress(student, unit.unit_id, progress)
                lesson_progress = []
                for lesson in lessons:
                    lesson_progress.append({
                        'lesson_id': lesson.lesson_id,
                        'title': lesson.title,
                        'completion': lesson_status[lesson.lesson_id]['html'],
                    })
                    activity_status = tracker.get_activity_status(progress, unit.unit_id, lesson.lesson_id)
                units.append({
                    'unit_id': unit.unit_id,
                    'title': unit.title,
                    'labels': list(course.get_unit_track_labels(unit)),
                    'completion': unit_completion[unit.unit_id],
                    'lessons': lesson_progress,
                    })
        return units

class StudentProgressRestHandler(BaseRESTHandler):
    """REST handler to manage retrieving student progress.

    Note:
        Inherits from BaseRESTHandler.

    Attributes:
        SCHEMA_VERSIONS (int): Current version of REST handler
        URL (str): Path to REST handler
        XSRF_TOKEN (str): Token used for xsrf security functions.

    """

    XSRF_TOKEN = 'student-progress-handler'
    SCHEMA_VERSIONS = ['1']

    URL = '/rest/modules/teacher_dashboard/student_progress'

    @classmethod
    def get_schema(cls):
        #TODO: implement a schema if necessary, not sure if needed since we aren't putting any data
        pass

    def get(self):
        """Get a students progress."""

        if not roles.Roles.is_course_admin(self.app_context):
            transforms.send_json_response(self, 401, 'Access denied.', {})
            return

        key = self.request.get('student')

        student = Student.get_by_email(key)
        course = self.get_course()

        units = StudentProgressTracker.get_detailed_progress(student, course)

        payload_dict = {
            'units': units,
            'student_name': student.name,
            'student_email': student.email
        }

        transforms.send_json_response(
            self, 200, '', payload_dict=payload_dict,
            xsrf_token=crypto.XsrfTokenManager.create_xsrf_token(
                self.XSRF_TOKEN))

class CourseSectionRestHandler(BaseRESTHandler):
    """REST handler to manage retrieving and updating course sections.

    Note:
        Inherits from BaseRESTHandler.

    Attributes:
        SCHEMA_VERSIONS (int): Current version of REST handler
        URL (str): Path to REST handler
        XSRF_TOKEN (str): Token used for xsrf security functions.

    """

    XSRF_TOKEN = 'section-handler'
    SCHEMA_VERSIONS = ['1']

    URL = '/rest/modules/teacher_dashboard/section'

    @classmethod
    def get_schema(cls):
        """Return the schema for the section editor."""
        return ResourceSection.get_schema(course=None, key=None)

    def get(self):
        """Get a section."""

        if not roles.Roles.is_course_admin(self.app_context):
            transforms.send_json_response(self, 401, 'Access denied.', {})
            return

        key = self.request.get('key')

        course_sections = teacher_entity.CourseSectionEntity.get_course_sections_for_user()

        if course_sections is not None:
            sorted_course_sections = sorted(course_sections.values(), key=lambda k: (k.section_year,
                                                                                 k.section_name.lower()))
        else:
            sorted_course_sections = {}

            #sorted(course_sections.values(), key=operator.attrgetter('section_year', 'section_name'))

        payload_dict = {
            'section_list': sorted_course_sections
        }

        if key:
            payload_dict['section'] = teacher_entity.CourseSectionEntity.get_course_for_user(str(key))

        transforms.send_json_response(
            self, 200, '', payload_dict=payload_dict,
            xsrf_token=crypto.XsrfTokenManager.create_xsrf_token(
                self.XSRF_TOKEN))

    def delete(self):
        """Deletes a section."""
        pass

    def put(self):
        """Inserts or updates a course section."""
        request = transforms.loads(self.request.get('request'))
        key = request.get('key')

        if not self.assert_xsrf_token_or_fail(
                request, self.XSRF_TOKEN, {}):
            return

        if not roles.Roles.is_course_admin(self.app_context):
            transforms.send_json_response(
                self, 401, 'Access denied.', {'key': key})
            return

        payload = request.get('payload')
        json_dict = transforms.loads(payload)
        python_dict = transforms.json_to_dict(
            json_dict, self.get_schema().get_json_schema_dict(),
            permit_none_values=True)

        version = python_dict.get('version')
        if version not in self.SCHEMA_VERSIONS:
            self.validation_error('Version %s not supported.' % version)
            return

        errors = []

        if key:
            key_after_save = key
            new_course_section = teacher_entity.CourseSectionEntity.get_course_for_user(key)

            students = new_course_section.students or {}
            emails = ""
            if 'students' in python_dict and python_dict['students'] is not None:
                emails = python_dict['students'].split(',')
            for email in emails:
                student = Student.get_by_email(email)
                if student:
                    student_info = {}
                    student_info['email'] = email
                    student_info['name'] = student.name
                    student_info['user_id'] = student.user_id
                    students[student.user_id] = student_info

            #sorted_students = sorted(students.values(), key=lambda k: (k['name']))

            if python_dict.get('name') != None:
                new_course_section.section_name = python_dict.get('name')
            if python_dict.get('active') != None:
                new_course_section.is_active = python_dict.get('active')
            if python_dict.get('description') != None:
                new_course_section.section_description = python_dict.get('description')
            if python_dict.get('year') != None:
                new_course_section.section_year = python_dict.get('year')

            course_section = teacher_entity.CourseSectionDTO.build(
                new_course_section.section_name, new_course_section.section_description,
                new_course_section.is_active, students, new_course_section.section_year)
            teacher_entity.CourseSectionEntity.update_course_section(key, course_section, errors)
        else:
            course_section = teacher_entity.CourseSectionDTO.build(
                python_dict.get('name'), python_dict.get('description'), python_dict.get('active'), {},
                python_dict.get('year'))
            key_after_save = teacher_entity.CourseSectionEntity.add_new_course_section(key, course_section, errors)

        if errors:
            self.validation_error('\n'.join(errors), key=key_after_save)
            return

        section = teacher_entity.CourseSectionEntity.get_course_for_user(key_after_save)
        if section:
            if section.students and len(section.students) > 0:
                for student in section.students.values():
                    student['unit_completion'] = StudentProgressTracker.get_unit_completion(Student.get_by_email(student[
                        'email']), self.get_course())
                    student['course_completion'] = StudentProgressTracker.get_overall_progress(Student.get_by_email(student[
                        'email']), self.get_course())
                    student['detailed_course_completion'] = StudentProgressTracker.get_detailed_progress(
                        Student.get_by_email(student['email']), self.get_course())

        payload_dict = {
            'key': key_after_save,
            'section': section,
            'section_list': teacher_entity.CourseSectionEntity.get_course_sections_for_user()
        }

        transforms.send_json_response(
            self, 200, 'Saved.', payload_dict)

class ResourceSection(AbstractResourceHandler):
    """Definition for the course section resource.

    Note:
        Inherits from AbstractResourceHandler.

    Attributes:
        TYPE (int): entity for resource

    """

    TYPE = 'course_section'

    @classmethod
    def get_resource(cls, course, key):
        """Loads a course section."""
        return teacher_entity.CourseSectionDAO.load(key)

    @classmethod
    def get_resource_title(cls, rsrc):
        """Returns course name."""
        return rsrc.name

    @classmethod
    def get_schema(cls, course, key):
        """Returns a schema definition of a section."""
        schema = schema_fields.FieldRegistry(
            'Section', description='section')
        schema.add_property(schema_fields.SchemaField(
            'version', '', 'string', optional=True, hidden=True))
        schema.add_property(schema_fields.SchemaField(
            'name', 'Name', 'string', optional=True))
        schema.add_property(schema_fields.SchemaField(
            'description', 'Description', 'text', optional=True))
        schema.add_property(schema_fields.SchemaField(
            'active', 'Active', 'boolean', optional=True))
        schema.add_property(schema_fields.SchemaField(
            'students', 'Students', 'string', optional=True))
        schema.add_property(schema_fields.SchemaField(
            'year', 'Year', 'string', optional=True))
        return schema

    @classmethod
    def get_data_dict(cls, course, key):
        return cls.get_resource(course, key).dict

    @classmethod
    def get_view_url(cls, rsrc):
        return None

    @classmethod
    def get_edit_url(cls, key):
        return None

def notify_module_enabled():
    """Handles things after module has been enabled."""

    def get_action(handler):
        """Redirects to teacher_dashboard."""
        handler.redirect('/modules/teacher_dashboard?action=teacher_dashboard&tab=%s' % handler.request.get('tab') or
                         TeacherHandler.DEFAULT_TAB)

    dashboard.DashboardHandler.add_nav_mapping(
        TeacherHandler.ACTION, 'Teacher')

    dashboard.DashboardHandler.get_actions.append('teacher_dashboard')
    setattr(dashboard.DashboardHandler, 'get_teacher_dashboard', get_action)

    #add post actions
    dashboard.DashboardHandler.add_custom_post_action('teacher_reg', TeacherHandler.post_teacher_reg)

    #add permissions for the dashboard sections
    dashboard.DashboardHandler.add_external_permission(
        ACCESS_ASSETS_PERMISSION, ACCESS_ASSETS_PERMISSION_DESCRIPTION)
    dashboard.DashboardHandler.add_external_permission(
        ACCESS_SETTINGS_PERMISSION, ACCESS_SETTINGS_PERMISSION_DESCRIPTION)
    dashboard.DashboardHandler.add_external_permission(
        ACCESS_ROLES_PERMISSION, ACCESS_ROLES_PERMISSION_DESCRIPTION)
    dashboard.DashboardHandler.add_external_permission(
        ACCESS_ANALYTICS_PERMISSION, ACCESS_ANALYTICS_PERMISSION_DESCRIPTION)
    dashboard.DashboardHandler.add_external_permission(
        ACCESS_SEARCH_PERMISSION, ACCESS_SEARCH_PERMISSION_DESCRIPTION)
    dashboard.DashboardHandler.add_external_permission(
        ACCESS_PEERREVIEW_PERMISSION, ACCESS_PEERREVIEW_PERMISSION_DESCRIPTION)
    dashboard.DashboardHandler.add_external_permission(
        ACCESS_SKILLMAP_PERMISSION, ACCESS_SKILLMAP_PERMISSION_DESCRIPTION)
    dashboard.DashboardHandler.add_external_permission(
        ACCESS_TEACHER_DASHBOARD_PERMISSION, ACCESS_TEACHER_DASHBOARD_PERMISSION_DESCRIPTION)


    dashboard.DashboardHandler.EXTRA_JS_HREF_LIST.append(
        '/modules/teacher_dashboard/resources/js/popup.js')
    dashboard.DashboardHandler.EXTRA_JS_HREF_LIST.append(
        '/modules/teacher_dashboard/resources/js/course_section_analytics.js')

    dashboard.DashboardHandler.EXTRA_CSS_HREF_LIST.append(
        '/modules/teacher_dashboard/resources/css/student_list.css')

    transforms.CUSTOM_JSON_ENCODERS.append(teacher_entity.CourseSectionEntity.json_encoder)

    #register tabs
    TeacherHandler.register_tabs()

    #hooks would go here, none needed for a basic module. yet....
    #dashboard.DashboardHandler.POST_SAVE_HOOKS.append(TeacherHandler.on_post_teacher_reg)
    #dashboard.DashboardHandler.POST_LOAD_HOOKS.append(TeacherHandler.on_post_teacher_reg)

    # dashboard.DashboardHandler.add_nav_mapping(
    #     TeacherHandler.ACTION, 'teacher_dashboard')
    dashboard.DashboardHandler.add_external_permission(
        ACCESS_TEACHER_DASHBOARD_PERMISSION, ACCESS_TEACHER_DASHBOARD_PERMISSION_DESCRIPTION)
    





def register_module():
    """Registers this module in the registry."""

    global_routes = [
        (os.path.join(RESOURCES_PATH, 'js', '.*'), tags.JQueryHandler),
        (os.path.join(RESOURCES_PATH, '.*'), tags.ResourcesHandler),
        (RESOURCES_PATH + '/js/popup.js', tags.IifeHandler),
        (RESOURCES_PATH + '/js/course_section_analytics.js', tags.IifeHandler)
       ]

    namespaced_routes = [
         (TeacherHandler.URL, TeacherHandler),
         (CourseSectionRestHandler.URL, CourseSectionRestHandler),
         (StudentProgressRestHandler.URL, StudentProgressRestHandler)
        ]

    global custom_module  # pylint: disable=global-statement
    custom_module = custom_modules.Module(
        'Teacher Dashboard Module',
        'A module provide teacher workflow.',
        global_routes, namespaced_routes,
        notify_module_enabled=notify_module_enabled)

    return custom_module
