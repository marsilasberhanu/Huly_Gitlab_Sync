export interface CreateIssueRequest {
  projectId?: string;
  title: string;
  description?: string;
  issueType?: string;
  priority?: number;
  status?: string;
  assignee?: string | null;
  milestone?: string | null;
  dueDate?: number | null;
  estimation?: number;
}