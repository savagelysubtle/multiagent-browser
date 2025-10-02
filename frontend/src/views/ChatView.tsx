import React from 'react';
import { CopilotChat } from '@copilotkit/react-ui';

export default function ChatView() {
  return (
    <div className="h-full w-full">
      <CopilotChat
        labels={{
          title: "AI Assistant",
          initialMessage: "Hello! I can help you with document editing, web browsing, and research tasks. What would you like to do?",
        }}
        // You can add more customization props here to match the existing UI
        // For example, to customize the chat input or message rendering
      />
    </div>
  );
}