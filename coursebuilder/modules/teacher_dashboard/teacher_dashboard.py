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

import appengine_config
import teacher_entity

from google.appengine.ext import db

from common import tags
from common import crypto

from models import courses
from models import custom_modules
from models import models
from models import roles

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
        register_tab('student', 'Student Profile', TeacherHandler)
        register_tab('teacher_reg', 'Register Teacher', TeacherHandler)

        # skill_map_visualization = analytics.Visualization(
        #     'skill_map',
        #     'Skill Map Analytics',
        #     'templates/skill_map_analytics.html',
        #     data_source_classes=[SkillMapDataSource])
        # tabs.Registry.register('analytics', 'skill_map', 'Skill Map',
        #                        [skill_map_visualization])

    def get_teacher_dashboard(self):
        in_tab = self.request.get('tab') or self.DEFAULT_TAB

        if in_tab == 'sections':
            return self.get_sections()
        elif in_tab == 'student':
            return self.get_student()
        elif in_tab =='teacher_reg':
            return self.get_teacher_reg()

    def get_sections(self):
        main_content = 'Course Section Content'

        self.render_page({
            'page_title': self.format_title('Sections'),
            'main_content': jinja2.utils.Markup(main_content)})

    def get_student(self):
        template_values = {}
        template_values['main_content'] = 'Student Dashboard Content'

        return template_values['main_content']

    def get_teacher_reg(self):
        template_values = {}
        template_values['teacher_reg_xsrf_token'] = self.create_xsrf_token('teacher_reg')
        main_content = self.get_template(
            'teacher_registration.html', [TEMPLATES_DIR]).render(template_values)

        self.render_page({
            'page_title': self.format_title('Teacher Registration'),
            'main_content': jinja2.utils.Markup(main_content)})

    def post_teacher_reg(self):
        template_values = []
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
        (os.path.join(RESOURCES_PATH, '.*'), tags.ResourcesHandler)
       ]

    namespaced_routes = [
         (TeacherHandler.URL, TeacherHandler)
        ]

    global custom_module  # pylint: disable=global-statement
    custom_module = custom_modules.Module(
        'Teacher Dashboard Module',
        'A module provide teacher workflow.',
        global_routes, namespaced_routes,
        notify_module_enabled=notify_module_enabled)

    return custom_module
