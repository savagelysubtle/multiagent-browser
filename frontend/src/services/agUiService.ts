
import { HttpAgent } from "@ag-ui/client";

const AGENT_URL = "/api/ag_ui/chat";

class AgUiService {
  private agent: HttpAgent;

  constructor() {
    console.log(`AgUiService: Initializing HttpAgent with URL: ${AGENT_URL}`);
    this.agent = new HttpAgent({
      url: AGENT_URL,
      agentId: "web-ui-agent",
      threadId: "main-thread",
    });
    console.log("AgUiService: HttpAgent initialized.", this.agent);
  }

  getAgent() {
    return this.agent;
  }
}

export const agUiService = new AgUiService();
