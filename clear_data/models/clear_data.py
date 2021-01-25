# -*- coding: utf-8 -*-

'''
Create Date:2017��9��1��

Author     :Administrator
'''
import datetime
import dateutil
import logging
import os
import time
import pdb
import logging
import odoo.tools
_logger = logging.getLogger(__name__)

from pytz import timezone

import odoo
from odoo import api, fields, models, tools, _
from odoo.exceptions import MissingError, UserError, ValidationError

class ClearDataModel(models.Model):
    _name='clear.data.model'
    
    name=fields.Char(string="Model group")
    internal_model_list=fields.Char(string='Always clear',descripton="Model in this list do not need installed. style like this:[string,string,...]")
    model_clear_ids=fields.Many2many("ir.model",'clear_data_ir_model_rel','group_id','model_id',domain=[('model','not in',['clear.data.model'])],ondelete="set null")
    auto_clear_ir_sequence=fields.Boolean(string="Auto clear ir sequence",defualt=True)
    date = fields.Date("Delete before this date")
    is_initial_balance = fields.Boolean('This is initial balance')

    
    @api.multi
    def action_do_clear(self):
        self.ensure_one()
        self._do_clear_internal_model()
        self._do_clear_model_relation()
        
        if self.auto_clear_ir_sequence:
            self._do_clear_ir_sequence()
        return True
    
    
    @api.multi
    def _do_clear_model_relation(self):
        
        self.ensure_one()
        
        for model_id in self.model_clear_ids:            
            if model_id:
               self._do_clear_by_model_name(model_id.model)
        
    @api.multi
    def _do_clear_internal_model(self):
        
        self.ensure_one()
        
        if not self.internal_model_list:
            return True
        
        model_list=[]
        
        try:
            model_list=eval(self.internal_model_list)
            if type(model_list) != list:
                raise UserError('Always clear model list format is incorrect!')
        except:
            raise UserError('Always clear model list format is incorrect!')
        
        if all(model_list):
            
            for model_name in model_list:
                self._do_clear_by_model_name(model_name)
                
        return True
    
    
    @api.multi
    def _do_clear_by_model_name(self,model_name):
        self.ensure_one()
        model_obj=self.env.get(model_name,None)
        if model_obj==None or not odoo.tools.table_exists(self._cr, model_obj._table):
            return
        lWhere = False
        self._cr.execute("SELECT column_name FROM information_schema.columns "
                   "WHERE table_name = '%s' AND column_name = 'date'" % (model_obj._table))
        if not self._cr.fetchone():
            sql = "DELETE FROM %s" % (model_obj._table,)
            lWhere = True
        else:
            sql="DELETE FROM %s WHERE date <= '%s'" % (model_obj._table, self.date, )

        self._cr.execute("SELECT column_name FROM information_schema.columns "
                   "WHERE table_name = '%s' AND column_name = 'date' AND column_name = 'is_initial_balance'" % (model_obj._table,))
        if self._cr.fetchone():
            sql = "DELETE FROM %s WHERE (date <= '%s' AND is_initial_balance = FALSE)" % (model_obj._table, self.date, )

        self._cr.execute("SELECT column_name FROM information_schema.columns "
                   "WHERE table_name = '%s' AND column_name = 'company_id'" % (model_obj._table))
        if self._cr.fetchone():
            if lWhere:
                sql += " WHERE company_id = %d" % self.env.user.company_id.id
            else:
                sql += " AND company_id = %d" % self.env.user.company_id.id
        self._cr.execute(sql)

    @api.multi
    def _do_clear_ir_sequence(self):
        cr=self._cr
        
        #清除不标准
        cr.execute("update ir_sequence set number_next=1")
        cr.execute("update ir_sequence_date_range set number_next=1")
        #清除标准
        seq_list=self.env['ir.sequence'].search([('implementation','=','standard')])
        if seq_list:
            for seq in seq_list:
                cr.execute("ALTER SEQUENCE ir_sequence_%03d RESTART WITH 1"%seq.id)