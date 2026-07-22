import apiClientRaw from "@hcengineering/api-client";

const apiClient = (apiClientRaw as any).default ?? apiClientRaw;

export interface HulyConnectionConfig {
  token: string;
  workspace: string;
  url: string;
}

function getEnv(name: string): string {
  const value = process.env[name];

  if (!value) {
    throw new Error(`Missing ${name}`);
  }

  return value;
}

export async function getHulyRestClient(
  connection?: HulyConnectionConfig
) {
  const token =
    connection?.token ?? getEnv("HULY_TOKEN");

  const workspace =
    connection?.workspace ?? getEnv("HULY_WORKSPACE_ID");

  const url =
    connection?.url ??
    process.env.HULY_URL ??
    "https://huly.app";

  return await apiClient.connectRest(url, {
    token,
    workspace,
  });
}

export async function closeClient(client: any) {
  if (typeof client.close === "function") {
    await client.close();
  }
}