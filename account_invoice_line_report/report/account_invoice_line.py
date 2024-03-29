# Copyright 2018 Tecnativa - David Vidal
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models
from odoo import tools
from functools import lru_cache


class AccountInvoiceLine(models.Model):
    # _inherit = "account.invoice.report"
    _name = "account.invoice.line"
    _description = "Invoices Detail"
    _auto = False
    _rec_name = 'invoice_date'
    _order = 'invoice_date desc'

    # ==== Invoice fields ====
    move_id = fields.Many2one('account.move', readonly=True)
    name = fields.Char('Invoice #', readonly=True)
    journal_id = fields.Many2one('account.journal', string='Journal', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    company_currency_id = fields.Many2one('res.currency', string='Company Currency', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    commercial_partner_id = fields.Many2one('res.partner', string='Partner Company', help="Commercial Entity")
    country_id = fields.Many2one('res.country', string="Country")
    invoice_user_id = fields.Many2one('res.users', string='Salesperson', readonly=True)
    move_type = fields.Selection([
        ('out_invoice', 'Customer Invoice'),
        ('in_invoice', 'Vendor Bill'),
        ('out_refund', 'Customer Credit Note'),
        ('in_refund', 'Vendor Credit Note'),
        ], readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Open'),
        ('cancel', 'Cancelled')
        ], string='Invoice Status', readonly=True)
    payment_state = fields.Selection(selection=[
        ('not_paid', 'Not Paid'),
        ('in_payment', 'In Payment'),
        ('paid', 'paid')
    ], string='Payment Status', readonly=True)
    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position', readonly=True)
    invoice_date = fields.Date(readonly=True, string="Invoice Date")
    nbr_lines = fields.Integer(string='Line Count', readonly=True)
    residual = fields.Float(string='Due Amount', readonly=True)
    amount_total = fields.Float(string='Total', readonly=True)


    # ==== Invoice line fields ====
    quantity = fields.Float(string='Product Quantity', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure', readonly=True)
    product_categ_id = fields.Many2one('product.category', string='Product Category', readonly=True)
    invoice_date_due = fields.Date(string='Due Date', readonly=True)
    account_id = fields.Many2one('account.account', string='Revenue/Expense Account', readonly=True, domain=[('deprecated', '=', False)])
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', groups="analytic.group_analytic_accounting")
    price_subtotal = fields.Float(string='Untaxed Total', readonly=True)
    price_average = fields.Float(string='Average Price', readonly=True, group_operator="avg")

    label = fields.Char(string='Label', readonly=True)
    discount = fields.Float(string='Discount', readonly=True)
    price_unit = fields.Float(string='Price', readonly=True)
    tax_base_amount = fields.Float(string='Vat', readonly=True)
    origin = fields.Char(string='Sale Order', readonly=True)
    cost = fields.Float(string='Cost', readonly=True)
    so_price = fields.Float(string='Order Price', readonly=True)
    narration = fields.Text(string='Ket', readonly=True)
    do = fields.Many2one('stock.picking', string='DO', readonly=True)

    _depends = {
        'account.move': [
            'name', 'state', 'move_type', 'partner_id', 'invoice_user_id', 'fiscal_position_id',
            'invoice_date', 'invoice_date_due', 'invoice_payment_term_id', 'partner_bank_id', 'invoice_origin',
            'narration', 'picking_ids',
        ],
        'account.move.line': [
            'quantity', 'price_subtotal', 'amount_residual', 'balance', 'amount_currency',
            'move_id', 'product_id', 'product_uom_id', 'account_id', 'analytic_account_id',
            'journal_id', 'company_id', 'currency_id', 'partner_id', 'price_unit',
        ],
        'product.product': ['product_tmpl_id'],
        'product.template': ['categ_id'],
        'uom.uom': ['category_id', 'factor', 'name', 'uom_type'],
        'res.currency.rate': ['currency_id', 'name'],
        'res.partner': ['country_id'],
        'stock.picking':['name'],
    }

    @property
    def _table_query(self):
        return '%s %s %s %s' % (self._select(), self._from(), self._where(), self._group_by())

    @api.model
    def _select(self):
        return '''
            SELECT
                line.id
                ,line.move_id
                ,line.product_id
                ,line.account_id
                ,line.analytic_account_id
                ,line.journal_id
                ,line.company_id
                ,line.company_currency_id
                ,line.partner_id AS commercial_partner_id
                ,move.name
                ,move.state
                ,move.move_type
                ,move.partner_id
                ,move.invoice_user_id 
                ,move.fiscal_position_id
                ,move.payment_state
                ,move.invoice_date
                ,move.invoice_date_due
                ,move.invoice_payment_term_id
                ,-line.balance * (move.amount_residual_signed / NULLIF(move.amount_total_signed, 0.0)) * (line.price_total / NULLIF(line.price_subtotal, 0.0))
                                                                            AS residual
                ,-line.balance * (line.price_total / NULLIF(line.price_subtotal, 0.0))    AS amount_total
                ,uom_template.id                                             AS product_uom_id
                ,template.categ_id                                           AS product_categ_id
                ,line.quantity / NULLIF(COALESCE(uom_line.factor, 1) / COALESCE(uom_template.factor, 1), 0.0)
                                                                            AS quantity
                ,-line.balance                                               AS price_subtotal
                ,-line.balance / NULLIF(COALESCE(uom_line.factor, 1) / COALESCE(uom_template.factor, 1), 0.0)
                                                                            AS price_average
                ,COALESCE(partner.country_id, commercial_partner.country_id) AS country_id
                ,1                                                           AS nbr_lines
                ,line.name as label
                ,line.discount as discount
                ,line.price_unit as price_unit
                ,sum(line.price_total-line.price_subtotal) as tax_base_amount
                ,move.invoice_origin as origin
                ,ip.value_float as cost
                ,sol.price_unit as so_price
                ,move.narration as narration
                ,sp.id as do
        '''

    @api.model
    def _from(self):
        return '''
            FROM account_move_line line
                LEFT JOIN res_partner partner ON partner.id = line.partner_id
                LEFT JOIN product_product product ON product.id = line.product_id
                LEFT JOIN account_account account ON account.id = line.account_id
                LEFT JOIN account_account_type user_type ON user_type.id = account.user_type_id
                LEFT JOIN product_template template ON template.id = product.product_tmpl_id
                LEFT JOIN product_category pc ON pc.id = template.categ_id
                LEFT JOIN uom_uom uom_line ON uom_line.id = line.product_uom_id
                LEFT JOIN uom_uom uom_template ON uom_template.id = template.uom_id
                INNER JOIN account_move move ON move.id = line.move_id
                LEFT JOIN res_partner commercial_partner ON commercial_partner.id = move.commercial_partner_id
                LEFT JOIN ir_property ip ON (ip.name='standard_price' AND ip.res_id= 'product.product,'||product.id)
				LEFT JOIN account_analytic_account alc ON alc.id=line.analytic_account_id
                LEFT JOIN sale_order_line_invoice_rel solir ON solir.invoice_line_id = line.id
                LEFT JOIN sale_order_line sol ON sol.id = solir.order_line_id
                LEFT JOIN sale_order so ON so.id = sol.order_id
                LEFT JOIN account_move_stock_picking_rel amsp ON amsp.account_move_id = move.id
                LEFT JOIN stock_picking sp ON sp.id = amsp.stock_picking_id
				JOIN {currency_table} ON currency_table.company_id = line.company_id
        '''.format(
            currency_table=self.env['res.currency']._get_query_currency_table({'multi_company': True, 'date': {'date_to': fields.Date.today()}}),
        )

    @api.model
    def _where(self):
        return '''
            WHERE move.move_type IN ('out_invoice'
                                , 'out_refund'
                                , 'in_invoice'
                                , 'in_refund'
                                , 'out_receipt'
                                , 'in_receipt')
                AND line.account_id IS NOT NULL
                AND NOT line.exclude_from_invoice_tab
        '''

    @api.model
    def _group_by(self):
        return '''
            GROUP BY
                line.id
                ,line.move_id
                ,line.product_id
                ,line.account_id
                ,line.analytic_account_id
                ,line.journal_id
                ,line.company_id
                ,line.currency_id
                ,line.partner_id
                ,move.name
                ,move.state
                ,move.move_type
                ,move.amount_residual_signed
                ,move.amount_total_signed
                ,move.partner_id
                ,move.invoice_user_id
                ,move.fiscal_position_id
                ,move.payment_state
                ,move.invoice_date
                ,move.invoice_date_due
                ,move.invoice_payment_term_id
                ,uom_template.id
                ,uom_line.factor
                ,template.categ_id
                ,COALESCE(partner.country_id, commercial_partner.country_id)
                ,line.name
                ,line.discount 
                ,line.price_unit 
                ,line.price_total
                ,move.invoice_origin
                ,ip.value_float
                ,sol.price_unit
                ,move.narration
                ,sp.id
        '''
