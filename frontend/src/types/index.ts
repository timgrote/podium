export interface Client {
  id: string
  name: string
  email: string | null
  company: string | null
  phone: string | null
  address: string | null
  notes: string | null
  created_at: string | null
  updated_at: string | null
}

export interface Employee {
  id: string
  first_name: string
  last_name: string
  email: string | null
  avatar_url: string | null
  is_active: boolean
}

export interface CompanySettings {
  [key: string]: string
}

export interface ContractTask {
  id: string
  contract_id: string
  sort_order: number
  name: string
  description: string | null
  amount: number
  billed_amount: number
  billed_percent: number
  created_at: string | null
  updated_at: string | null
}

export interface Contract {
  id: string
  project_id: string
  file_path: string | null
  total_amount: number
  signed_at: string | null
  notes: string | null
  tasks: ContractTask[]
  created_at: string | null
  updated_at: string | null
}

export interface InvoiceLineItem {
  id: string
  invoice_id: string
  sort_order: number
  name: string
  description: string | null
  quantity: number
  unit_price: number
  amount: number
  previous_billing: number
  created_at: string | null
}

export interface Invoice {
  id: string
  invoice_number: string
  project_id: string
  contract_id: string | null
  previous_invoice_id: string | null
  type: 'task' | 'list'
  description: string | null
  data_path: string | null
  pdf_path: string | null
  sent_status: 'unsent' | 'sent'
  paid_status: 'unpaid' | 'partial' | 'paid'
  total_due: number
  sent_at: string | null
  paid_at: string | null
  line_items?: InvoiceLineItem[]
  created_at: string | null
  updated_at: string | null
}

export interface ProposalTask {
  id: string
  proposal_id: string
  sort_order: number
  name: string
  description: string | null
  amount: number
  created_at: string | null
}

export interface Proposal {
  id: string
  project_id: string
  data_path: string | null
  pdf_path: string | null
  client_company: string | null
  client_contact_email: string | null
  total_fee: number
  engineer_key: string | null
  engineer_name: string | null
  engineer_title: string | null
  contact_method: string | null
  proposal_date: string | null
  sent_at: string | null
  status: 'draft' | 'sent' | 'accepted' | 'rejected'
  tasks: ProposalTask[]
  created_at: string | null
  updated_at: string | null
}

export interface ProjectNote {
  id: string
  project_id: string
  author_id: string | null
  author_name: string | null
  author_avatar_url: string | null
  content: string
  created_at: string | null
}

export interface ProjectSummary {
  id: string
  project_number: string | null
  job_code: string | null
  project_name: string | null
  status: string
  client_id: string | null
  client_name: string | null
  client_company: string | null
  client_email: string | null
  pm_id: string | null
  pm_name: string | null
  pm_email: string | null
  pm_avatar_url: string | null
  client_project_number: string | null
  location: string | null
  data_path: string | null
  total_contracted: number
  total_invoiced: number
  total_paid: number
  total_outstanding: number
  contracts: Contract[]
  invoices: Invoice[]
  proposals: Proposal[]
}

export interface ProjectDetail extends ProjectSummary {
  data_path: string | null
  notes: string | null
  client_phone: string | null
  current_invoice_id: string | null
  created_at: string | null
  updated_at: string | null
}

export interface TaskNote {
  id: string
  task_id: string
  author_id: string | null
  author_name: string | null
  author_avatar_url: string | null
  content: string
  created_at: string | null
}

export interface TaskCreatePayload {
  title: string
  description?: string | null
  parent_id?: string | null
  status?: string
  start_date?: string | null
  due_date?: string | null
  assignee_ids?: string[]
}

export interface TaskUpdatePayload {
  title?: string
  description?: string | null
  status?: string
  start_date?: string | null
  due_date?: string | null
  assignee_ids?: string[]
}

export interface TaskAssignee {
  id: string
  first_name: string
  last_name: string
}

export interface Task {
  id: string
  project_id: string
  parent_id: string | null
  title: string
  description: string | null
  status: 'todo' | 'in_progress' | 'blocked' | 'done' | 'canceled'
  priority: number | null
  start_date: string | null
  due_date: string | null
  sort_order: number
  created_by: string | null
  completed_at: string | null
  created_at: string | null
  updated_at: string | null
  assignees?: TaskAssignee[]
  notes?: TaskNote[]
  subtasks?: Task[]
}
