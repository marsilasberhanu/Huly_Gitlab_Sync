import crypto from "crypto";
import apiClientRaw from "@hcengineering/api-client";
import trackerRaw from "@hcengineering/tracker";
import taskRaw from "@hcengineering/task";
import { CreateIssueRequest } from "../types/issue";

const apiClient = (apiClientRaw as any).default ?? apiClientRaw;
const tracker = (trackerRaw as any).default ?? trackerRaw;
const task = (taskRaw as any).default ?? taskRaw;

function generateHulyId(): string {
  return crypto.randomBytes(12).toString("hex");
}

function getEnv(name: string): string {
  const value = process.env[name];

  if (!value) {
    throw new Error(`Missing ${name}`);
  }

  return value;
}

async function getClient() {
  const url = process.env.HULY_URL || "https://huly.app";

  const options: any = {
    token: getEnv("HULY_TOKEN"),
    workspace: getEnv("HULY_WORKSPACE_ID"),

    websocketFactory: apiClient.NodeWebSocketFactory,
    webSocketFactory: apiClient.NodeWebSocketFactory,
    wsFactory: apiClient.NodeWebSocketFactory,
    factory: apiClient.NodeWebSocketFactory
  };

  return await apiClient.connect(url, options);
}

async function closeClient(client: any) {
  if (typeof client.close === "function") {
    await client.close();
  }
}

export async function createIssue(payload: CreateIssueRequest) {
  if (!payload.title?.trim()) {
    throw new Error("title is required");
  }

  const client: any = await getClient();

  try {
    const projectId = payload.projectId || getEnv("HULY_PROJECT_ID");

    const project = await client.findOne(tracker.class.Project, {
      _id: projectId
    });

    if (!project) {
      throw new Error(`Project not found: ${projectId}`);
    }

    const issueTypeName = payload.issueType || "Issue";

    const issueType = await client.findOne(task.class.TaskType, {
      name: issueTypeName
    });

    if (!issueType) {
      throw new Error(`Issue type not found: ${issueTypeName}`);
    }

    const issueId = generateHulyId();

    const number = (project.sequence ?? 0) + 1;
    const identifier = `${project.identifier}-${number}`;

    const issueData = {
      title: payload.title.trim(),

      description: payload.description
        ? apiClient.markdown(payload.description)
        : null,

      assignee: payload.assignee ?? null,
      component: null,
      milestone: payload.milestone ?? null,

      number,
      status: payload.status || project.defaultIssueStatus || "tracker:status:Backlog",
      priority: payload.priority ?? 0,

      rank: "",
      comments: 0,
      subIssues: 0,

      dueDate: payload.dueDate ?? null,

      parents: [],
      reportedTime: 0,
      remainingTime: 0,
      estimation: payload.estimation ?? 0,
      reports: 0,
      relations: [],
      childInfo: [],

      kind: issueType._id,
      identifier
    };

    let result: any;

    if (typeof client.apply === "function") {
      const operations = client.apply(undefined, "tracker.createIssue");

      await operations.addCollection(
        tracker.class.Issue,
        project._id,
        tracker.ids.NoParent,
        tracker.class.Issue,
        "subIssues",
        issueData,
        issueId
      );

      result = await operations.commit();
    } else if (typeof client.addCollection === "function") {
      result = await client.addCollection(
        tracker.class.Issue,
        project._id,
        tracker.ids.NoParent,
        tracker.class.Issue,
        "subIssues",
        issueData,
        issueId
      );
    } else {
      const methods = [
        ...Object.keys(client),
        ...Object.getOwnPropertyNames(Object.getPrototypeOf(client))
      ];

      throw new Error(
        `No supported Huly issue creation method found. Available client methods: ${methods.join(", ")}`
      );
    }

    return {
      success: true,
      issueId,
      identifier,
      title: issueData.title,
      projectId: project._id,
      result
    };
  } finally {
    await closeClient(client);
  }
}