
import { HttpAgent } from "@ag-ui/client";

const AGENT_URL = "/api/ag_ui/chat";

class AgUiService {
  private agent: HttpAgent;

  constructor() {
    this.agent = new HttpAgent({
      url: AGENT_URL,
      agentId: "web-ui-agent",
      threadId: "main-thread",
    });
  }

  getAgent() {
    return this.agent;
  }
}

export const agUiService = new AgUiService();
