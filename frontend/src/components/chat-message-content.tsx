import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const URL_PATTERN = /(?<!["'(>])https?:\/\/[^\s<]+/gi;
const STREAMING_URL_SUFFIX_PATTERN = /[a-z0-9]$/i;

function normalizeUrlCandidate(url: string): string {
  return url.replace(/[),.;!?]+$/, "");
}

function buildLinkLabel(url: string): string {
  try {
    const parsedUrl = new URL(url);
    const normalizedPath = parsedUrl.pathname.replace(/\/$/, "");

    if (!normalizedPath || normalizedPath === "/") {
      return parsedUrl.hostname;
    }

    return `${parsedUrl.hostname}${normalizedPath}`;
  } catch {
    return "Link";
  }
}

function isProbablyCompleteUrl(url: string, isAtContentEnd: boolean): boolean {
  try {
    const parsedUrl = new URL(url);
    const hasRecognizableHost =
      parsedUrl.hostname.includes(".") || parsedUrl.hostname === "localhost";

    if (!hasRecognizableHost) {
      return false;
    }

    if (isAtContentEnd && STREAMING_URL_SUFFIX_PATTERN.test(url)) {
      return false;
    }

    return true;
  } catch {
    return false;
  }
}

function convertPlainUrlsToMarkdown(content: string, isStreaming: boolean): string {
  return content.replace(URL_PATTERN, (match, _url, offset) => {
    const normalizedUrl = normalizeUrlCandidate(match);
    const suffix = match.slice(normalizedUrl.length);
    const isAtContentEnd = offset + match.length === content.length;

    if (isStreaming && !isProbablyCompleteUrl(normalizedUrl, isAtContentEnd)) {
      return match;
    }

    const label = buildLinkLabel(normalizedUrl);
    return `[${label}](${normalizedUrl})${suffix}`;
  });
}

interface ChatMessageContentProps {
  content: string;
  renderMarkdown?: boolean;
  isStreaming?: boolean;
}

/**
 * Renders assistant chat messages with a constrained markdown surface.
 *
 * Raw HTML is intentionally disabled. Plain URLs are converted into markdown links
 * so the backend can return simple text while the UI still exposes clickable links.
 */
export function ChatMessageContent({
  content,
  renderMarkdown = false,
  isStreaming = false,
}: ChatMessageContentProps) {
  if (!renderMarkdown) {
    return <p className="whitespace-pre-wrap [overflow-wrap:anywhere]">{content}</p>;
  }

  return (
    <div
      className="chat-markdown [overflow-wrap:anywhere]"
      data-streaming={isStreaming ? "true" : undefined}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ node: _node, ...props }) => (
            <a {...props} target="_blank" rel="noreferrer noopener" />
          ),
        }}
      >
        {convertPlainUrlsToMarkdown(content, isStreaming)}
      </ReactMarkdown>
    </div>
  );
}
