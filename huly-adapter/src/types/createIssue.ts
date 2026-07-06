export interface CreateIssueRequest {
    projectId: string;

    title: string;

    description?: string;

    issueType: string;

    priority?: number;

    assignee?: string | null;

    milestone?: string | null;

    parentIssue?: string | null;

    estimate?: number;

    dueDate?: string | null;
}