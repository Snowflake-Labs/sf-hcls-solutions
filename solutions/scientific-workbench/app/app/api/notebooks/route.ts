import { querySnowflake } from "@/lib/snowflake"

const WORKSPACE = "SCIENTIFIC_WORKBENCH.CATALOG.SCIENTIFIC_WORKBENCH_NOTEBOOKS"
const [WS_DB, WS_SCHEMA, WS_NAME] = WORKSPACE.split(".")

const REGION_MAP: Record<string, string> = {
  "AWS_US_WEST_2": "us-west-2",
  "AWS_US_EAST_1": "us-east-1",
  "AWS_EU_WEST_1": "eu-west-1",
  "AWS_EU_CENTRAL_1": "eu-central-1",
  "AWS_AP_SOUTHEAST_1": "ap-southeast-1",
  "AWS_AP_SOUTHEAST_2": "ap-southeast-2",
  "AZURE_WESTUS2": "west-us-2.azure",
  "AZURE_EASTUS2": "east-us-2.azure",
  "GCP_US_CENTRAL1": "us-central1.gcp",
}

async function getSnowsightBase(): Promise<string | null> {
  try {
    const rows = await querySnowflake(
      "SELECT CURRENT_ACCOUNT() AS ACCT, CURRENT_REGION() AS REGION"
    ) as Record<string, string>[]
    if (!rows.length) return null
    const acct = (rows[0].ACCT ?? "").toLowerCase()
    const rawRegion = (rows[0].REGION ?? "").replace(/^PUBLIC\./, "")
    const region = REGION_MAP[rawRegion] ?? rawRegion.toLowerCase().replace(/_/g, "-")
    return `https://app.snowflake.com/${region}/${acct}`
  } catch {
    return null
  }
}

export async function GET() {
  try {
    const [rows, snowsightBase] = await Promise.all([
      querySnowflake(
        `LIST 'snow://workspace/${WORKSPACE}/versions/last/'`
      ),
      getSnowsightBase(),
    ])
    const notebooks = (rows as Record<string, unknown>[])
      .filter((r) => String(r.name ?? "").endsWith(".ipynb"))
      .map((r) => {
        const fullPath = String(r.name ?? "")
        const filename = fullPath.split("/").pop() ?? ""
        const name = filename.replace(/\.ipynb$/, "")
        const snowsight_url = snowsightBase
          ? `${snowsightBase}/#/workspaces/ws/${WS_DB}/${WS_SCHEMA}/${WS_NAME}/${filename}`
          : null
        return {
          name,
          filename,
          size: Number(r.size ?? 0),
          last_modified: String(r.last_modified ?? ""),
          workspace: WORKSPACE,
          snowsight_url,
        }
      })
    return Response.json({ notebooks })
  } catch (e) {
    const msg = e instanceof Error ? e.message : "Unknown error"
    return Response.json({ notebooks: [], error: msg })
  }
}
