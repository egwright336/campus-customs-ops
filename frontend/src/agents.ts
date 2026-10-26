import type { AgentName } from './types'

/** The five voices. Each reads differently: its own ink, its own typeface, its own seal letter. */
export const AGENTS: Record<AgentName, { title: string; epithet: string; seal: string; voice: string }> = {
  boss: { title: 'The Boss', epithet: 'who makes the final call', seal: 'B', voice: 'voice-boss' },
  inventory: { title: 'Inventory', epithet: 'keeper of the stockroom', seal: 'I', voice: 'voice-inventory' },
  accounting: { title: 'Accounting', epithet: 'keeper of the ledger', seal: 'A', voice: 'voice-accounting' },
  facilities: { title: 'Facilities', epithet: 'keeper of the lease', seal: 'F', voice: 'voice-facilities' },
  customer_service: {
    title: 'Customer Service',
    epithet: 'who writes the letters',
    seal: 'C',
    voice: 'voice-customer_service',
  },
}

export const AGENT_ORDER: AgentName[] = ['boss', 'inventory', 'accounting', 'facilities', 'customer_service']

export const TICKET_KIND: Record<string, string> = {
  customer_order: 'A customer order',
  rent_notice: 'A rent notice',
  price_override: 'A plea on price',
}

export const REQUEST_KIND: Record<string, string> = {
  invoice_payment: 'Pay an invoice',
  rent_payment: 'Pay the rent',
  purchase_order: 'Place a purchase order',
  price_override: 'Grant a lower price',
}

export const money = (n: number | null | undefined) =>
  n == null ? '—' : n.toLocaleString('en-US', { style: 'currency', currency: 'USD' })

export const prettyTool = (t: string) => t.replace(/_/g, ' ')
