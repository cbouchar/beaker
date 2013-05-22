import unittest
from bkr.inttest import data_setup, with_transaction
from bkr.inttest.client import run_client, ClientError, create_client_config
from bkr.server.model import Group, Activity
from turbogears.database import session

class GroupModifyTest(unittest.TestCase):

    def setUp(self):
        with session.begin():
            self.user = data_setup.create_user(password = 'asdf')
            self.group = data_setup.create_group(owner=self.user)
            self.client_config = create_client_config(username=self.user.user_name,
                                                      password='asdf')

            rand_user = data_setup.create_user(password = 'asdf')
            rand_user.groups.append(self.group)
            self.rand_client_config = create_client_config(username=rand_user.user_name,
                                                           password='asdf')
    def test_group_modify_no_criteria(self):
        try:
            out = run_client(['bkr', 'group-modify',
                              self.group.group_name],
                             config = self.client_config)
            self.fail('Must fail or die')
        except ClientError, e:
            self.assert_('Please specify an attribute to modify'
                         in e.stderr_output, e.stderr_output)


    def test_group_nonexistent(self):
        display_name = 'A New Group Display Name'
        try:
            out = run_client(['bkr', 'group-modify',
                              '--display-name', display_name,
                              'group-like-non-other'],
                             config = self.client_config)
            self.fail('Must fail or die')
        except ClientError, e:
            self.assert_('Group does not exist' in e.stderr_output,
                         e.stderr_output)

    def test_group_modify_invalid(self):
        display_name = 'A New Group Display Name'
        try:
            out = run_client(['bkr', 'group-modify',
                              '--display-name', display_name,
                              'random', self.group.group_name],
                             config = self.client_config)
            self.fail('Must fail or die')
        except ClientError, e:
            self.assert_('Exactly one group name must be specified' in
                         e.stderr_output, e.stderr_output)

    def test_group_modify_not_owner(self):
        display_name = 'A New Group Display Name'

        try:
            out = run_client(['bkr', 'group-modify',
                              '--display-name', display_name,
                              self.group.group_name],
                             config = self.rand_client_config)
            self.fail('Must fail or die')
        except ClientError, e:
            self.assert_('You are not an owner of group' in
                         e.stderr_output, e.stderr_output)

    def test_group_modify_display_name(self):
        display_name = 'A New Group Display Name'
        out = run_client(['bkr', 'group-modify',
                          '--display-name', display_name,
                          self.group.group_name],
                         config = self.client_config)

        with session.begin():
            session.refresh(self.group)
            group = Group.by_name(self.group.group_name)
            self.assertEquals(group.display_name, display_name)
            self.assertEquals(group.activity[-1].action, u'Changed')
            self.assertEquals(group.activity[-1].field_name, u'Display Name')
            self.assertEquals(group.activity[-1].user.user_id,
                              self.user.user_id)
            self.assertEquals(group.activity[-1].new_value, display_name)
            self.assertEquals(group.activity[-1].service, u'XMLRPC')

    def test_group_modify_group_name(self):
        group_name = 'mynewgroup'
        out = run_client(['bkr', 'group-modify',
                          '--group-name', group_name,
                          self.group.group_name],
                         config = self.client_config)

        with session.begin():
            session.refresh(self.group)
            group = Group.by_name(group_name)
            self.assertEquals(group.group_name, group_name)
            self.assertEquals(group.activity[-1].action, u'Changed')
            self.assertEquals(group.activity[-1].field_name, u'Name')
            self.assertEquals(group.activity[-1].user.user_id,
                              self.user.user_id)
            self.assertEquals(group.activity[-1].new_value, group_name)
            self.assertEquals(group.activity[-1].service, u'XMLRPC')

    def test_group_modify_group_display_names(self):
        display_name = 'Shiny New Display Name'
        group_name = 'shinynewgroup'
        out = run_client(['bkr', 'group-modify',
                          '--display-name', display_name,
                          '--group-name', group_name,
                          self.group.group_name],
                         config = self.client_config)

        with session.begin():
            session.refresh(self.group)
            group = Group.by_name(group_name)
            self.assertEquals(group.display_name, display_name)
            self.assertEquals(group.group_name, group_name)

    def test_group_modify_add_member(self):
        with session.begin():
            user = data_setup.create_user()

        out = run_client(['bkr', 'group-modify',
                          '--add-member', user.user_name,
                          self.group.group_name],
                         config = self.client_config)

        with session.begin():
            session.refresh(self.group)
            group = Group.by_name(self.group.group_name)
            self.assert_(user.user_name in
                         [u.user_name for u in group.users])

        try:
            out = run_client(['bkr', 'group-modify',
                              '--add-member', 'idontexist',
                              self.group.group_name],
                             config = self.client_config)
            self.fail('Must fail or die')
        except ClientError, e:
            self.assert_('User does not exist' in
                         e.stderr_output, e.stderr_output)

        try:
            out = run_client(['bkr', 'group-modify',
                              '--add-member', user.user_name,
                              self.group.group_name],
                             config = self.client_config)
            self.fail('Must fail or die')
        except ClientError, e:
            self.assert_('User %s is already in group' % user.user_name in
                         e.stderr_output, e.stderr_output)

        with session.begin():
            session.refresh(self.group)
            group = Group.by_name(self.group.group_name)
            self.assertEquals(group.activity[-1].action, u'Added')
            self.assertEquals(group.activity[-1].field_name, u'User')
            self.assertEquals(group.activity[-1].user.user_id,
                              self.user.user_id)
            self.assertEquals(group.activity[-1].new_value, user.user_name)
            self.assertEquals(group.activity[-1].service, u'XMLRPC')

    def test_group_modify_remove_member(self):
        with session.begin():
            user = data_setup.create_user()
            self.group.users.append(user)
            session.flush()
            self.assert_(user in self.group.users)

        out = run_client(['bkr', 'group-modify',
                          '--remove-member', user.user_name,
                          self.group.group_name],
                         config = self.client_config)

        with session.begin():
            session.refresh(self.group)
            group = Group.by_name(self.group.group_name)
            self.assert_(user.user_name not in
                         [u.user_name for u in group.users])

        try:
            out = run_client(['bkr', 'group-modify',
                              '--remove-member', 'idontexist',
                              self.group.group_name],
                             config = self.client_config)
            self.fail('Must fail or die')
        except ClientError, e:
            self.assert_('User does not exist' in
                         e.stderr_output, e.stderr_output)
        try:
            out = run_client(['bkr', 'group-modify',
                              '--remove-member', user.user_name,
                              self.group.group_name],
                             config = self.client_config)
            self.fail('Must fail or die')
        except ClientError, e:
            self.assert_('No user %s in group' % user.user_name in
                         e.stderr_output, e.stderr_output)

        try:
            out = run_client(['bkr', 'group-modify',
                              '--remove-member', self.user.user_name,
                              self.group.group_name],
                             config = self.client_config)
            self.fail('Must fail or die')
        except ClientError, e:
            self.assert_('You are the only owner of group' in
                         e.stderr_output, e.stderr_output)

        with session.begin():
            session.refresh(self.group)
            group = Group.by_name(self.group.group_name)
            self.assertEquals(group.activity[-1].action, u'Removed')
            self.assertEquals(group.activity[-1].field_name, u'User')
            self.assertEquals(group.activity[-1].user.user_id,
                              self.user.user_id)
            self.assertEquals(group.activity[-1].old_value, user.user_name)
            self.assertEquals(group.activity[-1].new_value, '')
            self.assertEquals(group.activity[-1].service, u'XMLRPC')