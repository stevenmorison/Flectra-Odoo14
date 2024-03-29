# Copyright 2018 Tecnativa - David Vidal
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models


class AccountInvoiceReport(models.Model):
    _inherit = "account.invoice.report"

    market_place_id = fields.Many2one(comodel_name="market.place", string="Market")

    @api.model
    def _select(self):
        select_str = super(AccountInvoiceReport, self)._select()
        select_str += """
            , move.invoice_marketplace as market_place_id
            """
        return select_str

    @api.model
    def _group_by(self):
        group_by_str = super(AccountInvoiceReport, self)._group_by()
        group_by_str += ", move.invoice_marketplace"
        return group_by_str
