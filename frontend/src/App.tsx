import { useState } from "react";

import { ChatWidget } from "@/components/chat-widget";
import { MarketingShell } from "@/components/marketing-shell";

function App() {
  const [chatOpen, setChatOpen] = useState(false);

  return (
    <>
      <MarketingShell onOpenChat={() => setChatOpen(true)} />
      <ChatWidget open={chatOpen} onOpenChange={setChatOpen} />
    </>
  );
}

export default App;
