# -*- coding: utf-8 -*-
import logging
import pypinyin
from odoo import api, fields, models, SUPERUSER_ID
from odoo.exceptions import AccessDenied

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = ['res.users']

    ding_user_phone = fields.Char(string='钉钉登录手机', index=True)
    ding_user_id = fields.Char(string='钉钉访问令牌', index=True)

    @api.model
    def auth_oauth(self, provider, params):
        if provider == 'dingtalk':
            user = self.search([('ding_user_id', '=', params)], limit=1)
            if not user:
                _logger.info(">>>员工关联的用户不正确或则未关联成功.")
                return False
            return (self.env.cr.dbname, user[0].login, params)
        else:
            return super(ResUsers, self).auth_oauth(provider, params)

    @api.model
    def _check_credentials(self, password, env):
        try:
            return super(ResUsers, self)._check_credentials(password, env)
        except AccessDenied:
            res = self.with_user(SUPERUSER_ID).search([('id', '=', self.env.uid), ('ding_user_id', '=', password)])
            if not res:
                raise

    def create_user_by_employee(self, employee_id, password, active=True):
        """
        通过员工创建Odoo用户
        安装依赖 pypinyin:  pip install pypinyin
        """
        employee = self.env['hr.employee'].with_user(SUPERUSER_ID).search([('id', '=', employee_id)])
        if employee:
            # 账号生成改为格式：姓名全拼+手机号末四位@企业邮箱域名
            email_name1 = pypinyin.slug(employee.name, separator='')  # 全拼
            # email_name1 = pypinyin.slug(employee.name, style=Style.FIRST_LETTER, separator='') # 首字母
            email_name2 = employee.mobile_phone[7:]  # 取手机号末四位
            email_name = email_name1 + email_name2
            # 这里后续可以加个开关，让管理员自己决定使用其他域名或企业邮箱域名
            url = self.env['ir.config_parameter'].with_user(SUPERUSER_ID).get_param('mail.catchall.domain')
            if url:
                email_host = url
            else:
                email_host = 'dingtalk.com'
            email_count = len(self.search([('login', 'like', email_name)]).with_user(SUPERUSER_ID))
            if email_count > 0:
                user = self.env['res.users'].with_user(SUPERUSER_ID).search([('login', '=', email_name + '@' + email_host)])
                values = {
                    'user_id': user.id
                }
                employee.with_user(SUPERUSER_ID).write(values)
            else:
                email = email_name + '@' + email_host
                # 获取不重复的姓名
                name = employee.name
                name_count = len(self.search([('name', 'like', name)]).with_user(SUPERUSER_ID))
                if name_count > 0:
                    name = name + str(name_count + 1)
                # 创建Odoo用户
                values = {
                    'active': active,
                    "login": email,
                    "password": password,
                    "name": name,
                    'email': employee.work_email,
                    'groups_id': self.env.ref('base.group_user')
                }
                user = self.with_user(SUPERUSER_ID).create(values)
                # 首次自动创建odoo用户后发送钉钉工作通知给该员工
                msg = {
                    'msgtype': 'text',
                    'text': {
                        "content": "尊敬的{},欢迎加入odoo,您的登陆名为{}，初始登陆密码为{}，请登陆后及时修改密码！".format(name, email, password),
                    }
                }
                self.env['dindin.work.message'].with_user(SUPERUSER_ID).send_work_message(userstr=employee.ding_id, msg=msg)
                # 注册成功后，自动关联员工与用户
                values = {
                    'user_id': user.id
                }
                employee.with_user(SUPERUSER_ID).write(values)
