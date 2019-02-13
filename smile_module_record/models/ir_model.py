# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2014 Smile (<http://www.smile.fr>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import api, models

import logging
_logger = logging.getLogger(__name__)

def get_index(l, k):
    l = [i for i, j in l][::-1]
    return len(l) - l.index(k) - 1


class IrModel(models.Model):
    _inherit = 'ir.model'

    def _get_linked_models(self, models, required):
        linked_models = {}
        for model in models:
            linked_models.setdefault(model, {})
            for field_name, field in self.env[model]._fields.items():
                _logger.info("fields %s:%s" % (field_name, field))
                if field.type in ('many2one', 'many2many') and field.store \
                        and field.comodel_name in models and field.required == required:
                    linked_models[model].setdefault(field.comodel_name, []).append('%s:id' % field_name)
        return linked_models

    @api.multi
    def get_ordered_model_graph(self, models):
        ordered_models = []
        models = [model.model for model in models if self.env[model.model]._auto and hasattr(self.env[model.model], 'get_fields_to_export')]
        required_linked_models = self._get_linked_models(models, required=True)
        while required_linked_models:
            level_models = []
            _logger.info("lin %s" % required_linked_models.keys())
            for model in list(required_linked_models):
                if not required_linked_models[model]:
                    level_models.append((model, []))
                    del required_linked_models[model]
            for model in required_linked_models.keys():
                for linked_model in list(required_linked_models[model]):
                    if linked_model in dict(level_models):
                        del required_linked_models[model][linked_model]
            ordered_models.extend(level_models)

        not_required_linked_models = self._get_linked_models(models, required=False)
        for index, (model, model_fields) in enumerate(ordered_models):
            not_required_link_fields = sum(not_required_linked_models[model].values(), [])
            ordered_models[index] = (model, list(set(self.env[model].get_fields_to_export()) - set(not_required_link_fields)))

        for model in not_required_linked_models:
            for linked_model, link_fields in not_required_linked_models[model].items():
                index = get_index(ordered_models, model)
                if index > get_index(ordered_models, linked_model):
                    ordered_models[index] = (model, ordered_models[index][1] + link_fields)
                else:
                    ordered_models.append((model, ['id'] + link_fields))

        return ordered_models


class IrModelData(models.Model):
    _inherit = 'ir.model.data'

    def import_data(self, cr, uid, fields_to_import, datas, mode='init', current_module='',
                    noupdate=False, context=None, filename=None):
        if 'id' not in fields_to_import and 'complete_name' in fields_to_import:
            position = 0
            for data in datas:
                module, name = data[fields_to_import.index('complete_name')].split('.')
                ids = self.search(cr, uid, [('module', '=', module), ('name', '=', name)], limit=1)
                vals = dict(zip(fields_to_import, data))
                if ids:
                    self.write(cr, uid, ids, vals, context)
                else:
                    self.create(cr, uid, vals, context)
                position += 1
            return position, 0, 0, 0
        return super(IrModelData, self).import_data(cr, uid, fields_to_import, datas, mode,
                                                    current_module, noupdate, context, filename)
