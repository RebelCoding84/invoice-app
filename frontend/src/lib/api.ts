export type InvoiceCreateRequest = {
  customer: {
    name: string;
    email?: string;
    address?: string;
    vat_id?: string;
  };
  line: {
    description: string;
    quantity: string;
    unit_price: string;
    vat_percent: string;
  };
  payment_method?: string;
  notes?: string;
  currency?: string;
  issue_date?: string | null;
  due_date?: string | null;
  options?: {
    generate_finvoice?: boolean;
    enable_backup?: boolean;
  };
};

export type InvoiceCreateResponse = {
  invoice_no: string;
  totals: Record<string, string>;
  has_finvoice: boolean;
};

let apiBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";
let apiKey = process.env.NEXT_PUBLIC_API_KEY || "";

export const getApiBaseUrl = () => apiBaseUrl;
export const setApiBaseUrl = (value: string) => {
  apiBaseUrl = value.trim();
};

export const getApiKey = () => apiKey;
export const setApiKey = (value: string) => {
  apiKey = value.trim();
};

const buildHeaders = () => {
  const headers: Record<string, string> = {
    "Content-Type": "application/json"
  };
  if (apiKey) {
    headers["X-API-Key"] = apiKey;
  }
  return headers;
};

export const createInvoice = async (
  payload: InvoiceCreateRequest
): Promise<InvoiceCreateResponse> => {
  const response = await fetch(`${apiBaseUrl}/api/v1/invoices`, {
    method: "POST",
    headers: buildHeaders(),
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || "Invoice creation failed");
  }
  return response.json();
};

const fetchFile = async (path: string): Promise<Blob> => {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    headers: apiKey ? { "X-API-Key": apiKey } : undefined
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || "Download failed");
  }
  return response.blob();
};

export const downloadPdf = (invoiceNo: string) =>
  fetchFile(`/api/v1/invoices/${invoiceNo}/pdf`);

export const downloadFinvoice = (invoiceNo: string) =>
  fetchFile(`/api/v1/invoices/${invoiceNo}/finvoice`);
