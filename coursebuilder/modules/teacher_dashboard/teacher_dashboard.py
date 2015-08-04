__author__ = 'ehiller@css.edu'


# Module to support custom teacher views in CourseBuilder dashboard
# Views include:
#       Class Roster - paginated list of students in teacher's section
#       CourseAdmin/Create Section - page for course admins to add a section for a teacher.
#           This will create a teacher entity
#       Student Dashboard - view of a single student's performance in the course
#       Section Gradebook - show course completion
#       More to be added

import logging
import jinja2
import os
import operator

import appengine_config
import teacher_entity

from google.appengine.api import users

from common import tags
from common import crypto

from models import courses
from models import custom_modules
from models import models
from models import roles
from models import transforms
from models.models import Student
from models.progress import UnitLessonCompletionTracker

from controllers.utils import BaseRESTHandler

from common.resource import AbstractResourceHandler
from common import schema_fields

#since we are extending the dashboard, probably want to dashboard stuff
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

#setup custom module for, needs to be referenced later
custom_module = None

class BaseDashboardExtension(object):
    ACTION = None

    @classmethod
    def is_readonly(cls, course):
        return course.app_context.get_environ()[
                'course'].get('prevent_translation_edits')

    @classmethod
    def format_readonly_message(cls):
        pass
        #return safe_dom.Element('P').add_text(
        #    'Translation console is currently disabled. '
        #    'Course administrator can enable it via I18N Settings.')

    @classmethod
    def register(cls):
        def get_action(handler):
            cls(handler).render()
        dashboard.DashboardHandler.add_custom_get_action(cls.ACTION, get_action)
        #dashboard.DashboardHandler.map_action_to_permission(
        #    'get_%s' % cls.ACTION, ACCESS_PERMISSION)

    @classmethod
    def unregister(cls):
        dashboard.DashboardHandler.remove_custom_get_action(cls.ACTION)
        dashboard.DashboardHandler.unmap_action_to_permission(
            'get_%s' % cls.ACTION)

    def __init__(self, handler):
        """Initialize the class with a request handler.

        Args:
            handler: modules.dashboard.DashboardHandler. This is the handler
                which will do the rendering.
        """
        self.handler = handler

class TeacherHandler(dashboard.DashboardHandler):
    ACTION = 'teacher_dashboard'
    DEFAULT_TAB = 'sections'

    URL = '/modules/teacher_dashboard'

    XSRF_TOKEN_NAME = ''

    #def __init__(self, handler):
    #    super(TeacherHandler, self).__init__(handler)

    @classmethod
    def register_tabs(cls):

        def register_tab(key, label, handler, href=None):
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
        register_tab('teacher_reg', 'Register Teacher', TeacherHandler)

    def get_teacher_dashboard(self):
        in_tab = self.request.get('tab') or self.DEFAULT_TAB
        tab_action = self.request.get('tab_action') or None

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
        main_content = self.get_template(
            'teacher_sections.html', [TEMPLATES_DIR]).render({})

        self.render_page({
            'page_title': self.format_title('Sections'),
            'main_content': jinja2.utils.Markup(main_content)})

    def get_student_dashboard(self):

        student_email = self.request.get('student') or None #email will be in the request if opened from student list
        # view, otherwise just show dropdown

        students = []
        course_sections = teacher_entity.CourseSectionEntity.get_course_sections_for_user()
        for course_section in course_sections.values():
            for student in course_section.students.values():
                if not student in students:
                    students.append(student)

        if student_email:
            student = Student.get_by_email(student_email)


        if (student):
            course = self.get_course()
            units = StudentProgressTracker.get_detailed_progress(student, course)
        else:
            units = None

        main_content = self.get_template(
            'student_detailed_progress.html', [TEMPLATES_DIR]).render(
                {
                    'units': units,
                    'student': student,
                    'students': students
                })

        self.render_page({
            'page_title': self.format_title('Student Dashboard'),
            'main_content': jinja2.utils.Markup(main_content)
        })


    def get_roster(self):
        template_values = {}
        template_values['add_student_xsrf_token'] = crypto.XsrfTokenManager.create_xsrf_token(CourseSectionRestHandler.XSRF_TOKEN)

        units = self.get_course().get_units()
        units_filtered = filter(lambda x: x.type == 'U', units)
        template_values['units'] = units_filtered

        course_section_id = self.request.get('section')

        course_section = teacher_entity.CourseSectionEntity.get_course_for_user(course_section_id)

        if course_section.students and len(course_section.students) > 0:
            for student in course_section.students.values():
                student['unit_completion'] = StudentProgressTracker.get_unit_completion(Student.get_by_email(student[
                    'email']), self.get_course())
                student['course_completion'] = StudentProgressTracker.get_overall_progress(Student.get_by_email(student[
                    'email']), self.get_course())

        template_values['students_json'] = transforms.dumps(course_section.students, {})

        if course_section:
            template_values['section'] = course_section

        main_content = self.get_template(
            'student_list.html', [TEMPLATES_DIR]).render(template_values)

        self.render_page({
            'page_title': self.format_title('Student List'),
            'main_content': jinja2.utils.Markup(main_content)})


    def get_teacher_reg(self):
        template_values = {}
        template_values['teacher_reg_xsrf_token'] = self.create_xsrf_token('teacher_reg')
        main_content = self.get_template(
            'teacher_registration.html', [TEMPLATES_DIR]).render(template_values)

        self.render_page({
            'page_title': self.format_title('Teacher Registration'),
            'main_content': jinja2.utils.Markup(main_content)})

    def post_teacher_reg(self):
        email = self.request.get('email')
        school = self.request.get('school')

        #ehiller - check if the teacher already exists
        teacher = teacher_entity.Teacher.get_by_email(email)

        alerts = []

        if teacher:
            template_values = {}
            alerts.append('Teacher already registered')

            template_values['teacher_reg_xsrf_token'] = self.create_xsrf_token('teacher_reg')
            template_values['alert_messages'] = '\n'.join(alerts)
            main_content = self.get_template(
                'teacher_registration.html', [TEMPLATES_DIR]).render(template_values)

            self.render_page({
                'page_title': self.format_title('Teacher Dashboard'),
                'main_content': jinja2.utils.Markup(main_content)
                },
                'teacher_dashboard',
                'teacher_reg'
            )
        else:
            teacher_entity.Teacher.add_new_teacher_for_user(email, school, '', alerts)

            template_values = {}

            template_values['alert_messages'] = '\n'.join(alerts)
            template_values['teacher_reg_xsrf_token'] = self.create_xsrf_token('teacher_reg')
            main_content = self.get_template(
                'teacher_registration.html', [TEMPLATES_DIR]).render(template_values)

            self.render_page({
                'page_title': self.format_title('Teacher Dashboard'),
                'main_content': jinja2.utils.Markup(main_content)
                },
                'teacher_dashboard',
                'teacher_reg'
            )

class StudentProgressTracker(object):

    @classmethod
    def get_unit_completion(cls, student, course):
        tracker = course.get_progress_tracker()

        progress = tracker.get_or_create_progress(student)

        return tracker.get_unit_percent_complete(student)

    @classmethod
    def get_overall_progress(cls, student, course):
        tracker = course.get_progress_tracker()

        progress = tracker.get_or_create_progress(student)

        unit_completion = tracker.get_unit_percent_complete(student)

        course_completion = 0
        for unit_completion_value in unit_completion.values():
            course_completion += unit_completion_value

        course_completion = (course_completion / len(unit_completion)) * 100

        return course_completion

    @classmethod
    def get_detailed_progress(cls, student, course):
        units = []

        tracker = course.get_progress_tracker()

        progress = tracker.get_or_create_progress(student)
        unit_completion = tracker.get_unit_percent_complete(student)

        # for unit in course.get_units():
        #     if course.get_parent_unit(unit.unit_id):
        #         continue
        #     if unit.unit_id in unit_completion:
        #        # logging.info('Barok >>>>>>>>>>>>>>> percent completion unit_id = %s: %s', unit.unit_id, unit_completion[unit.unit_id])
        for unit in course.get_units():
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
    """REST handler to manage retrieving student progress."""

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
    """REST handler to manage skills."""

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

        payload_dict = {
            'key': key_after_save,
            'section': section,
            'section_list': teacher_entity.CourseSectionEntity.get_course_sections_for_user()
        }

        transforms.send_json_response(
            self, 200, 'Saved.', payload_dict)

class ResourceSection(AbstractResourceHandler):

    TYPE = 'course_section'

    @classmethod
    def get_resource(cls, course, key):
        return teacher_entity.CourseSectionDAO.load(key)

    @classmethod
    def get_resource_title(cls, rsrc):
        return rsrc.name

    @classmethod
    def get_schema(cls, course, key):

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

#Not needed as far as I know, at least, until we run into a scenario where we might need to define roles specific to
# this module (can edit students maybe, something like that)
# def permissions_callback(app_context):
#     return [
#             roles.Permission(ACCESS_ASSETS_PERMISSION, ACCESS_ASSETS_PERMISSION_DESCRIPTION)
#         ]

def notify_module_enabled():
    def get_action(handler):
        handler.redirect('/modules/teacher_dashboard?action=teacher_dashboard&tab=%s' % handler.request.get('tab') or
                         TeacherHandler.DEFAULT_TAB)

    dashboard.DashboardHandler.add_nav_mapping(
        TeacherHandler.ACTION, 'Teacher')

    dashboard.DashboardHandler.get_actions.append('teacher_dashboard')
    setattr(dashboard.DashboardHandler, 'get_teacher_dashboard', get_action)

    #add post actions
    dashboard.DashboardHandler.add_custom_post_action('teacher_reg', TeacherHandler.post_teacher_reg)

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

    dashboard.DashboardHandler.EXTRA_JS_HREF_LIST.append(
        '/modules/teacher_dashboard/resources/js/popup.js')
    dashboard.DashboardHandler.EXTRA_JS_HREF_LIST.append(
        '/modules/teacher_dashboard/resources/js/course_section_analytics.js')

    dashboard.DashboardHandler.EXTRA_CSS_HREF_LIST.append(
        '/modules/teacher_dashboard/resources/css/student_list.css')

    transforms.CUSTOM_JSON_ENCODERS.append(teacher_entity.CourseSectionEntity.json_encoder)

    #register tabs
    TeacherHandler.register_tabs()

    #Don't need to register permissions here, dashboard module takes care of that
    #roles.Roles.register_permissions(
    #    custom_module, permissions_callback)

    #here's where I would register my entities, IF I HAD ANY
    #courses.ADDITIONAL_ENTITIES_FOR_COURSE_IMPORT.add(ResourceBundleEntity)
    #courses.ADDITIONAL_ENTITIES_FOR_COURSE_IMPORT.add(I18nProgressEntity)

    #register handlers (register is in BaseDashboardExtension)
    #TeacherHandler.register()

    #hooks would go here, none needed for a basic module. yet....


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
