'''Create a teacher's entity'''

__author__ = 'barok.imana@trincoll.edu'


from models import entities
from models import models
from models import transforms

from google.appengine.ext import db
from google.appengine.api import namespace_manager
from google.appengine.api import users

import appengine_config
import logging
import datetime
import json

from common import utils as common_utils


# We want to use memcache for both objects that exist and do not exist in the
# datastore. If object exists we cache its instance, if object does not exist
# we cache this object below.
NO_OBJECT = {}

class Teacher(entities.BaseEntity):
    """Teacher data specific to a course instance, modeled after the student Entity"""
    enrolled_on = db.DateTimeProperty(auto_now_add=True, indexed=True)
    user_id = db.StringProperty(indexed=True)
    name = db.StringProperty(indexed=False)
    additional_fields = db.TextProperty(indexed=False)
    is_enrolled = db.BooleanProperty(indexed=False)

    # Additional field for teachers
    sections = db.StringProperty(indexed=False)
    school = db.StringProperty(indexed=False)
    email = db.StringProperty(indexed=False)

    _PROPERTY_EXPORT_BLACKLIST = [
        additional_fields,  # Suppress all additional_fields items.
        # Convenience items if not all additional_fields should be suppressed:
        #'additional_fields.xsrf_token',  # Not PII, but also not useful.
        #'additional_fields.form01',  # User's name on registration form.
        name]

    @classmethod
    def safe_key(cls, db_key, transform_fn):
        return db.Key.from_path(cls.kind(), transform_fn(db_key.id_or_name()))

    def for_export(self, transform_fn):
        """Creates an ExportEntity populated from this entity instance."""
        assert not hasattr(self, 'key_by_user_id')
        model = super(Teacher, self).for_export(transform_fn)
        model.user_id = transform_fn(self.user_id)
        # Add a version of the key that always uses the user_id for the name
        # component. This can be used to establish relationships between objects
        # where the student key used was created via get_key(). In general,
        # this means clients will join exports on this field, not the field made
        # from safe_key().
        model.key_by_user_id = self.get_key(transform_fn=transform_fn)
        return model

    @property
    def email(self):
        return self.key().name()

    # additional method for Teacher's entity
    @property
    def sections(self):
        return

    @classmethod
    def _memcache_key(cls, key):
        """Makes a memcache key from primary key."""
        return 'entity:teacher:%s' % key

    @classmethod
    def _memcache_key(cls, key):
        """Makes a memcache key from primary key."""
        return 'entity:teacher:%s' % key

    def put(self):
        """Do the normal put() and also add the object to memcache."""
        result = super(Teacher, self).put()
        models.MemcacheManager.set(self._memcache_key(self.key().name()), self)
        return result

    def delete(self):
        """Do the normal delete() and also remove the object from memcache."""
        super(Teacher, self).delete()
        models.MemcacheManager.delete(self._memcache_key(self.key().name()))

    @classmethod
    def add_new_teacher_for_user(
        cls, email, school, additional_fields):
        TeacherProfileDAO.add_new_teacher_for_user(email, school, additional_fields)

    @classmethod
    def get_by_email(cls, email):
        return Teacher.get_by_key_name(email.encode('utf8'))

    @classmethod
    def get_student_by_user_id(cls):
        """Loads user and student and asserts both are present."""
        user = users.get_current_user()
        if not user:
            raise Exception('No current user.')
        teacher = cls.get_by_email(user.email())
        if not teacher:
            raise Exception('Teacher instance corresponding to user %s not '
                            'found.' % user.email())
        return teacher

    @classmethod
    def get_teacher_by_email(cls, email):
        """Returns enrolled teacher or None."""
        # ehiller - not sure if memcache check is in the right place, feel like we might want to do that after
        # checking datastore. this depends on what memcachemanager returns if a teacher hasn't been set there yet but
        #  still actually exists.
        teacher = models.MemcacheManager.get(cls._memcache_key(email))
        if NO_OBJECT == teacher:
            return None
        if not teacher:
            teacher = Teacher.get_by_email(email)
            if teacher:
                models.MemcacheManager.set(cls._memcache_key(email), teacher)
            else:
                models.MemcacheManager.set(cls._memcache_key(email), NO_OBJECT)
        if teacher: #ehiller - removed isEnrolled check, don't think we still need a teacher to be
        # enrolled to get their data back
            return teacher
        else:
            return None

    def get_key(self, transform_fn=None):
        """Gets a version of the key that uses user_id for the key name."""
        if not self.user_id:
            raise Exception('Teacher instance has no user_id set.')
        user_id = transform_fn(self.user_id) if transform_fn else self.user_id
        return db.Key.from_path(Teacher.kind(), user_id)

    @classmethod
    def get_teacher_by_user_id(cls, user_id):
        teachers = cls.all().filter(cls.user_id.name, user_id).fetch(limit=2)
        if len(teachers) == 2:
            raise Exception(
                'There is more than one teacher with user_id %s' % user_id)
        return teachers[0] if teachers else None

    def has_same_key_as(self, key):
        """Checks if the key of the teacher and the given key are equal."""
        return key == self.get_key()

class TeacherProfileDAO(object):
    """All access and mutation methods for PersonalProfile and Teacher."""

    TARGET_NAMESPACE = appengine_config.DEFAULT_NAMESPACE_NAME

    # Each hook is called back after update() has completed without raising
    # an exception.  Arguments are:
    # profile: The PersonalProfile object for the user
    # student: The Student object for the user
    # Subsequent arguments are identical to the arguments list to the update()
    # call.  Not documented here so as to not get out-of-date.
    # The return value from hooks is discarded.  Since these hooks run
    # after update() has succeeded, they should run as best-effort, rather
    # than raising exceptions.
    UPDATE_POST_HOOKS = []

    # Each hook is called back after _add_new_student_for_current_user has
    # completed without raising an exception.  Arguments are:
    # student: The Student object for the user.
    # The return value from hooks is discarded.  Since these hooks run
    # after update() has succeeded, they should run as best-effort, rather
    # than raising exceptions.
    ADD_STUDENT_POST_HOOKS = []

    @classmethod
    def _memcache_key(cls, key):
        """Makes a memcache key from primary key."""
        return 'entity:personal-profile:%s' % key

    @classmethod
    def _get_profile_by_user_id(cls, user_id):
        """Loads profile given a user_id and returns Entity object."""
        old_namespace = namespace_manager.get_namespace()
        try:
            namespace_manager.set_namespace(cls.TARGET_NAMESPACE)

            profile = models.MemcacheManager.get(
                cls._memcache_key(user_id), namespace=cls.TARGET_NAMESPACE)
            if profile == NO_OBJECT:
                return None
            if profile:
                return profile
            profile = models.PersonalProfile.get_by_key_name(user_id)
            models.MemcacheManager.set(
                cls._memcache_key(user_id), profile if profile else NO_OBJECT,
                namespace=cls.TARGET_NAMESPACE)
            return profile
        finally:
            namespace_manager.set_namespace(old_namespace)

    @classmethod
    def _add_new_profile(cls, user_id, email):
        """Adds new profile for a user_id and returns Entity object."""
        #ehiller - if for some reason we can't share student profile, I don't think a teacher would care, we probably
        # don't even need this function
        #if not CAN_SHARE_STUDENT_PROFILE.value:
        #    return None

        old_namespace = namespace_manager.get_namespace()
        try:
            namespace_manager.set_namespace(cls.TARGET_NAMESPACE)

            profile = models.PersonalProfile(key_name=user_id)
            profile.email = email
            profile.enrollment_info = '{}'
            profile.put()
            return profile
        finally:
            namespace_manager.set_namespace(old_namespace)

    @classmethod
    def _update_global_profile_attributes(
            cls, profile,
            email=None, legal_name=None, nick_name=None,
            date_of_birth=None, is_enrolled=None, final_grade=None,
            course_info=None):
        """Modifies various attributes of Student's Global Profile."""
        # TODO(psimakov): update of email does not work for student
        if email is not None:
            profile.email = email

        if legal_name is not None:
            profile.legal_name = legal_name

        if nick_name is not None:
            profile.nick_name = nick_name

        if date_of_birth is not None:
            profile.date_of_birth = date_of_birth

        if not (is_enrolled is None and final_grade is None and
                        course_info is None):

            # Defer to avoid circular import.
            from controllers import sites
            course = sites.get_course_for_current_request()
            course_namespace = course.get_namespace_name()

            if is_enrolled is not None:
                enrollment_dict = transforms.loads(profile.enrollment_info)
                enrollment_dict[course_namespace] = is_enrolled
                profile.enrollment_info = transforms.dumps(enrollment_dict)

            if final_grade is not None or course_info is not None:
                course_info_dict = {}
                if profile.course_info:
                    course_info_dict = transforms.loads(profile.course_info)
                if course_namespace in course_info_dict.keys():
                    info = course_info_dict[course_namespace]
                else:
                    info = {}
                if final_grade:
                    info['final_grade'] = final_grade
                if course_info:
                    info['info'] = course_info
                course_info_dict[course_namespace] = info
                profile.course_info = transforms.dumps(course_info_dict)

    @classmethod
    def _update_course_profile_attributes(
            cls, teacher, nick_name=None, is_enrolled=None, labels=None, sections=None):
        """Modifies various attributes of Student's Course Profile."""

        if nick_name is not None:
            teacher.name = nick_name

        if is_enrolled is not None:
            teacher.is_enrolled = is_enrolled

        if labels is not None:
            teacher.labels = labels

        if sections is not None:
            teacher.sections = sections

    @classmethod
    def _update_attributes(
            cls, profile, teacher,
            email=None, legal_name=None, nick_name=None,
            date_of_birth=None, is_enrolled=None, final_grade=None,
            course_info=None, labels=None, sections=None):
        """Modifies various attributes of Teacher and Profile."""

        if profile:
            cls._update_global_profile_attributes(
                profile, email=email, legal_name=legal_name,
                nick_name=nick_name, date_of_birth=date_of_birth,
                is_enrolled=is_enrolled, final_grade=final_grade,
                course_info=course_info)

        if teacher:
            cls._update_course_profile_attributes(
                teacher, nick_name=nick_name, is_enrolled=is_enrolled,
                labels=labels, sections=sections)

    @classmethod
    def _put_profile(cls, profile):
        """Does a put() on profile objects."""
        if not profile:
            return
        profile.put()
        models.MemcacheManager.delete(
            cls._memcache_key(profile.user_id),
            namespace=cls.TARGET_NAMESPACE)

    @classmethod
    def get_profile_by_user_id(cls, user_id):
        """Loads profile given a user_id and returns DTO object."""
        profile = cls._get_profile_by_user_id(user_id)
        if profile:
            return models.PersonalProfileDTO(personal_profile=profile)
        return None

    # This method is going to largely depend on how we plan to register
    # users as teachers

    @classmethod
    def add_new_teacher_for_user(
            cls, email,  school, additional_fields):

        student_by_email = models.Student.get_by_email(email)

        teacher = cls._add_new_teacher_for_user(
            student_by_email.user_id, email, student_by_email.name, school, additional_fields)

        return teacher


    @classmethod
    def _add_new_teacher_for_user(
            cls, user_id, email, nick_name, school, additional_fields):
        teacher = cls._add_new_teacher_for_user_in_txn(
            user_id, email, nick_name, school, additional_fields)
        #ehiller - may need to add hooks for adding a teacher
        #common_utils.run_hooks(cls.ADD_STUDENT_POST_HOOKS, student)
        return teacher

    @classmethod
    @db.transactional(xg=True)
    def _add_new_teacher_for_user_in_txn(
            cls, user_id, email, nick_name, school, additional_fields):
        """Create new teacher."""

        # create profile if does not exist
        # profile = cls._get_profile_by_user_id(user_id)
        # if not profile:
        #     profile = cls._add_new_profile(user_id, email)

        # create new teacher
        teacher = Teacher.get_by_email(email)
        if not teacher:
            # TODO(psimakov): we must move to user_id as a key
            teacher = Teacher(key_name=email)

        # update profile
        #cls._update_attributes(
        #    profile, teacher, nick_name=nick_name, is_enrolled=True,
         #   labels=labels)

        # update student
        teacher.user_id = user_id
        teacher.additional_fields = additional_fields
        teacher.school = school
        teacher.name = nick_name

        # put both
        #cls._put_profile(profile)
        teacher.put()

        return teacher


class CourseSectionEntity(object):

    """Course section information"""
    created_datetime = str(datetime.MINYEAR)
    section_id = ""
    section_name = ""
    section_description = ""
    students = ""
    is_active = False

    def __init__(self, course_section_decoded):
        self.created_datetime = course_section_decoded['created_datetime']
        self.section_id = course_section_decoded['section_id']
        self.section_name = course_section_decoded['section_name']
        self.section_description = course_section_decoded['section_description']
        self.students = course_section_decoded['students']
        self.is_active = course_section_decoded['is_active']

    #ehiller - need ability to translate JSON data to CourseSectionEntity
    def transform_course_data(self):
        #ehiller - is_active is the main this I care about here, we can leave the datetime as a string until we
        # actually need to do any datetime operations on it
        if self.is_active == 'True' or self.is_active == 'true':
            _is_active = True
        else:
            _is_active = False

        self.is_active = _is_active

    @classmethod
    def add_new_course_section(cls, course_sections, section_id, section_name, section_description = None,
                               is_active=True):

        #initialize new course section
        course_section = CourseSectionEntity()
        course_section.section_id = section_id
        course_section.section_name = section_name
        course_section.section_description = section_description
        course_section.is_active = is_active

        #add new section to list of sections passed in. this should add it by reference and set the collection
        course_sections[section_id] = course_section

    @classmethod
    def get_course_sections_for_user(cls):
        user = users.get_current_user()

        if not user:
            return None

        teacher = Teacher.get_by_email(user.email)

        if not teacher:
            return None

        course_sections = []

        course_sections_decoded = json.loads(teacher.sections)

        for course_section_decoded in course_sections_decoded:
            course_section = CourseSectionEntity(course_section_decoded)
            course_sections.append(course_section)

        return course_sections

