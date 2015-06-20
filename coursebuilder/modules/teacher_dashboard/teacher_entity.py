'''Create a teacher's entity'''

__author__ = 'barok.imana@trincoll.edu'

from models import entities

class Teacher(BaseEntity):
    """Teacher data specific to a course instance, modeled after the student Entity"""
    enrolled_on = db.DateTimeProperty(auto_now_add=True, indexed=True)
    user_id = db.StringProperty(indexed=True)
    name = db.StringProperty(indexed=False)
    additional_fields = db.TextProperty(indexed=False)
    is_enrolled = db.BooleanProperty(indexed=False)

    # Additional field for teachers
    students = db.StringProperty(indexed=False)



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
    def is_transient(self):
        return False

    @property
    def email(self):
        return self.key().name()

    @property
    def profile(self):
        return TeacherProfileDAO.get_profile_by_user_id(self.user_id)

    # additional method for Teacher's entity
    @property
    def students(self):
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
        MemcacheManager.set(self._memcache_key(self.key().name()), self)
        return result

    def delete(self):
        """Do the normal delete() and also remove the object from memcache."""
        super(Teacher, self).delete()
        MemcacheManager.delete(self._memcache_key(self.key().name()))

    @classmethod
    def add_new_teacher_for_current_user(
        cls, nick_name, additional_fields, handler, labels=None):
        TeacherProfileDAO.add_new_teacher_for_current_user(
            nick_name, additional_fields, handler, labels)

    @classmethod
    def get_by_email(cls, email):
        return Teacher.get_by_key_name(email.encode('utf8'))

    @classmethod
    def get_enrolled_teacher_by_email(cls, email):
        """Returns enrolled teacher or None."""
        teacher = MemcacheManager.get(cls._memcache_key(email))
        if NO_OBJECT == teacher:
            return None
        if not teacher:
            teacher = Teacher.get_by_email(email)
            if student:
                MemcacheManager.set(cls._memcache_key(email), teacher)
            else:
                MemcacheManager.set(cls._memcache_key(email), NO_OBJECT)
        if teacher and teacher.is_enrolled:
            return teahcer
        else:
            return None

    @classmethod
    def _get_user_and_student(cls):
        """Loads user and student and asserts both are present."""
        user = users.get_current_user()
        if not user:
            raise Exception('No current user.')
        teacher = Teacher.get_by_email(user.email())
        if not teacher:
            raise Exception('Student instance corresponding to user %s not '
                            'found.' % user.email())
        return user, teacher

    @classmethod
    def rename_current(cls, new_name):
        """Gives student a new name."""
        _, teacher = cls._get_user_and_student()
        TeacherProfileDAO.update(
            student.user_id, teacher.email, nick_name=new_name)

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
                'There is more than one student with user_id %s' % user_id)
        return teachers[0] if teachers else None

    def has_same_key_as(self, key):
        """Checks if the key of the student and the given key are equal."""
        return key == self.get_key()

    def get_labels_of_type(self, label_type):
        if not self.labels:
            return set()
        label_ids = LabelDAO.get_set_of_ids_of_type(label_type)
        return set([int(label) for label in
                    common_utils.text_to_list(self.labels)
                    if int(label) in label_ids])

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

        profile = MemcacheManager.get(
            cls._memcache_key(user_id), namespace=cls.TARGET_NAMESPACE)
        if profile == NO_OBJECT:
            return None
        if profile:
            return profile
        profile = PersonalProfile.get_by_key_name(user_id)
        MemcacheManager.set(
            cls._memcache_key(user_id), profile if profile else NO_OBJECT,
            namespace=cls.TARGET_NAMESPACE)
        return profile
    finally:
        namespace_manager.set_namespace(old_namespace)

@classmethod
def _add_new_profile(cls, user_id, email):
    """Adds new profile for a user_id and returns Entity object."""
    if not CAN_SHARE_STUDENT_PROFILE.value:
        return None

    old_namespace = namespace_manager.get_namespace()
    try:
        namespace_manager.set_namespace(cls.TARGET_NAMESPACE)

        profile = PersonalProfile(key_name=user_id)
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
        cls, teacher, nick_name=None, is_enrolled=None, labels=None, students=None):
    """Modifies various attributes of Student's Course Profile."""

    if nick_name is not None:
        teacher.name = nick_name

    if is_enrolled is not None:
        teacher.is_enrolled = is_enrolled

    if labels is not None:
        teacher.labels = labels

    if students is not None:
        teacher.students = students

@classmethod
def _update_attributes(
        cls, profile, teacher,
        email=None, legal_name=None, nick_name=None,
        date_of_birth=None, is_enrolled=None, final_grade=None,
        course_info=None, labels=None):
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
            labels=labels, students=students)

@classmethod
def _put_profile(cls, profile):
    """Does a put() on profile objects."""
    if not profile:
        return
    profile.put()
    MemcacheManager.delete(
        cls._memcache_key(profile.user_id),
        namespace=cls.TARGET_NAMESPACE)

@classmethod
def get_profile_by_user_id(cls, user_id):
    """Loads profile given a user_id and returns DTO object."""
    profile = cls._get_profile_by_user_id(user_id)
    if profile:
        return PersonalProfileDTO(personal_profile=profile)
    return None

@classmethod
def add_new_profile(cls, user_id, email):
    return cls._add_new_profile(user_id, email)

# This method is going to largely depend on how we plan to register
# users as teachers

@classmethod
def add_new_teacher_for_current_user(
        cls, nick_name, additional_fields, handler, labels=None):
    user = users.get_current_user()

    student_by_uid = Student.get_student_by_user_id(user.user_id())
    is_valid_student = (student_by_uid is None or
                        student_by_uid.user_id == user.user_id())
    assert is_valid_student, (
        'Student\'s email and user id do not match.')

    student = cls._add_new_student_for_current_user(
        user.user_id(), user.email(), nick_name, additional_fields, labels)

    try:
        cls._send_welcome_notification(handler, student)
    except Exception, e:  # On purpose. pylint: disable=broad-except
        logging.error(
            'Unable to send welcome notification; error was: ' + str(e))


@classmethod
def _add_new_student_for_current_user(
        cls, user_id, email, nick_name, additional_fields, labels=None):
    student = cls._add_new_student_for_current_user_in_txn(
        user_id, email, nick_name, additional_fields, labels)
    common_utils.run_hooks(cls.ADD_STUDENT_POST_HOOKS, student)
    return student

@classmethod
@db.transactional(xg=True)
def _add_new_teacher_for_current_user_in_txn(
        cls, user_id, email, nick_name, additional_fields, labels=None):
    """Create new or re-enroll old student."""

    # create profile if does not exist
    profile = cls._get_profile_by_user_id(user_id)
    if not profile:
        profile = cls._add_new_profile(user_id, email)

    # create new student or re-enroll existing
    student = Student.get_by_email(email)
    if not student:
        # TODO(psimakov): we must move to user_id as a key
        student = Student(key_name=email)

    # update profile
    cls._update_attributes(
        profile, teacher, nick_name=nick_name, is_enrolled=True,
        labels=labels)

    # update student
    student.user_id = user_id
    student.additional_fields = additional_fields

    # put both
    cls._put_profile(profile)
    student.put()

    return student
'''
@classmethod
def _send_welcome_notification(cls, handler, student):
    if not cls._can_send_welcome_notifications(handler):
        return

    if services.unsubscribe.has_unsubscribed(student.email):
        return

    course_settings = handler.app_context.get_environ()['course']
    course_title = course_settings['title']
    sender = cls._get_welcome_notifications_sender(handler)

    assert sender, 'Must set welcome_notifications_sender in course.yaml'

    context = {
        'student_name': student.name,
        'course_title': course_title,
        'course_url': handler.get_base_href(handler),
        'unsubscribe_url': services.unsubscribe.get_unsubscribe_url(
            handler, student.email)
    }

    if course_settings.get('welcome_notifications_subject'):
        subject = jinja2.Template(unicode(
            course_settings['welcome_notifications_subject']
        )).render(context)
    else:
        subject = 'Welcome to ' + course_title

    if course_settings.get('welcome_notifications_body'):
        body = jinja2.Template(unicode(
            course_settings['welcome_notifications_body']
        )).render(context)
    else:
        jinja_environment = handler.app_context.fs.get_jinja_environ(
            [os.path.join(
                appengine_config.BUNDLE_ROOT, 'views', 'notifications')],
            autoescape=False)
        body = jinja_environment.get_template('welcome.txt').render(context)

    services.notifications.send_async(
        student.email, sender, WELCOME_NOTIFICATION_INTENT,
        body, subject, audit_trail=context,
    )

@classmethod
def _can_send_welcome_notifications(cls, handler):
    return (
        services.notifications.enabled() and services.unsubscribe.enabled()
        and cls._get_send_welcome_notifications(handler))

@classmethod
def _get_send_welcome_notifications(cls, handler):
    return handler.app_context.get_environ().get(
        'course', {}
    ).get('send_welcome_notifications', False)

@classmethod
def _get_welcome_notifications_sender(cls, handler):
    return handler.app_context.get_environ().get(
        'course', {}
    ).get('welcome_notifications_sender')
'''
@classmethod
def get_enrolled_student_by_email_for(cls, email, app_context):
    """Returns student for a specific course."""
    old_namespace = namespace_manager.get_namespace()
    try:
        namespace_manager.set_namespace(app_context.get_namespace_name())
        return Student.get_enrolled_student_by_email(email)
    finally:
        namespace_manager.set_namespace(old_namespace)

@classmethod
def update(
        cls, user_id, email, legal_name=None, nick_name=None,
        date_of_birth=None, is_enrolled=None, final_grade=None,
        course_info=None, labels=None, profile_only=False):
    profile, student = cls._update_in_txn(
        user_id, email, legal_name, nick_name, date_of_birth, is_enrolled,
        final_grade, course_info, labels, profile_only)
    common_utils.run_hooks(
        cls.UPDATE_POST_HOOKS, profile, student, user_id, email,
        legal_name, nick_name, date_of_birth, is_enrolled,
        final_grade, course_info, labels, profile_only)

@classmethod
@db.transactional(xg=True)
def _update_in_txn(
        cls, user_id, email, legal_name=None, nick_name=None,
        date_of_birth=None, is_enrolled=None, final_grade=None,
        course_info=None, labels=None, profile_only=False):
    """Updates a student and/or their global profile."""
    student = None
    if not profile_only:
        student = Student.get_by_email(email)
        if not student:
            raise Exception('Unable to find student for: %s' % user_id)

    profile = cls._get_profile_by_user_id(user_id)
    if not profile:
        profile = cls.add_new_profile(user_id, email)

    cls._update_attributes(
        profile, student, email=email, legal_name=legal_name,
        nick_name=nick_name, date_of_birth=date_of_birth,
        is_enrolled=is_enrolled, final_grade=final_grade,
        course_info=course_info, labels=labels)

    cls._put_profile(profile)
    if not profile_only:
        student.put()

    return profile, student

