Looking at the data structure for projects

Projects have: 
- Name
- Client
- ClientPM (project Manager)
- List of Contacts
- Contract
- ID (Client-Name)
- List of Contracts
- List of Invoices
- Total Invoiced
- Total Contracted
- Total Paid
- Status
- DataPath (dropbox folder, TBG/HeronLakes)

Contracts have:
- FilePath (Path to PDF of signed contract/proposal)
- List of Tasks
- Total Contracted
- Total Invoiced
- List of Invoices

TaskInvoices are invoices based on our proposals with tasks. 
They have:
- Contract (optional)
- List of InvoiceTasks
- DataPath(path to excel/GoogleSheet)
- PDFPath(path to PDF of sent invoice)
- PaidStatus (Paid/Unpaid)
- SentStatus (Sent/Unsent)
- Total Due

ListInvoices are invoices that are mostly just time and expense invoices for us. Usually just a list of hours and rates. They have:
- Contract (optional)
- Description
- List of items (hourly rates for us)
- DataPath(path to excel/GoogleSheet)
- PDFPath(path to PDF of sent invoice)
- PaidStatus (Paid/Unpaid)
- SentStatus (Sent/Unsent)
- Total Due

InvoiceTasks have:
- Number (1,2,3, etc)
- Name
- Description
- Amount

Proposals are just unsigned contracts for a project.
They have:
- DataPath (path to word doc/google sheet)
- PDFPath (path to sent/generated PDF)
- ClientCompany
- ClientContact (email sent to)
- List of Tasks
- Total Fee