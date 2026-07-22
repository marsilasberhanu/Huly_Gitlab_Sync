import apiClientRaw from "@hcengineering/api-client";
import trackerRaw from "@hcengineering/tracker";

import type { HulyConnectionConfig } from "./huly.client.js";


const apiClient = (apiClientRaw as any).default ?? apiClientRaw;
const tracker = (trackerRaw as any).default ?? trackerRaw;


function getEnv(name: string): string {
  const value = process.env[name];

  if (!value) {
    throw new Error(`Missing ${name}`);
  }

  return value;
}


async function getRestClient(
  connection?: HulyConnectionConfig
) {
  const url =
    connection?.url ??
    process.env.HULY_URL ??
    "https://huly.app";

  const token =
    connection?.token ??
    getEnv("HULY_TOKEN");

  const workspace =
    connection?.workspace ??
    getEnv("HULY_WORKSPACE_ID");

  return await apiClient.connectRest(url, {
    token,
    workspace,
  });
}


async function closeClient(client: any) {
  if (typeof client.close === "function") {
    await client.close();
  }
}


export async function listIssues(
  projectId?: string,
  limit = 20,
  connection?: HulyConnectionConfig
) {
  const client: any = await getRestClient(connection);

  try {
    const targetProjectId =
      projectId ??
      getEnv("HULY_PROJECT_ID");

    const project = await client.findOne(
      tracker.class.Project,
      {
        _id: targetProjectId,
      }
    );

    if (!project) {
      throw new Error(
        `Project not found: ${targetProjectId}`
      );
    }

    const issues = await client.findAll(
      tracker.class.Issue,
      {
        space: project._id,
      },
      {
        limit,
      }
    );

    const hulyUrl =
      connection?.url ??
      process.env.HULY_URL ??
      "https://huly.app";

    const workspace =
      connection?.workspace ??
      process.env.HULY_WORKSPACE_ID ??
      "";

    const normalizedIssues = issues.map(
      (issue: any) => {
        let description = "";

        if (typeof issue.description === "string") {
          description = issue.description;
        } else if (issue.description) {
          description = JSON.stringify(
            issue.description
          );
        }

        return {
          projectId: project._id,
          projectIdentifier: project.identifier,
          id: issue._id,
          identifier: issue.identifier,
          title: issue.title,
          description,
          status: issue.status,
          priority: issue.priority,
          number: issue.number,
          modifiedOn: issue.modifiedOn,
          createdOn: issue.createdOn,
          url:
            `${hulyUrl}/workbench/${workspace}` +
            `/tracker/${project._id}/issues`,
        };
      }
    );

    normalizedIssues.sort((a: any, b: any) => {
      return (
        Number(b.modifiedOn ?? 0) -
        Number(a.modifiedOn ?? 0)
      );
    });

    return {
      success: true,
      projectId: project._id,
      projectIdentifier: project.identifier,
      count: normalizedIssues.length,
      issues: normalizedIssues,
    };
  } finally {
    await closeClient(client);
  }
}
