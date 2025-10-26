// Shared markdown/text cleaning utilities used across chat components

// Escape HTML special characters to prevent injection; do not escape single quotes
export function escapeHtml(str: string): string {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// Decode a set of common HTML entities, including many apostrophe variants and &nbsp;
export function unescapeBasicEntities(t: string): string {
  return String(t)
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&#x27;/gi, "'")
    .replace(/&apos;/gi, "'")
    // handle broken/spaced numeric entities like '& #39;' or '&# 39;'
    .replace(/&\s*#\s*39;?/g, "'")
    .replace(/&\s*#\s*x?\s*27;?/gi, "'")
    .replace(/&nbsp;/g, ' ');
}

// Render a safe, limited subset of markdown with links, code, headings, bold/italics, and line breaks
export function renderLimitedMarkdown(raw: unknown): string {
  if (raw === null || raw === undefined) return '';
  let s0 = unescapeBasicEntities(String(raw));

  // Strip any leaked inline-style artifact fragments if present
  s0 = s0.replace(/#[0-9a-fA-F]{3,6};\s*text-decoration:underline;">/g, '');

  // 1) Extract code-fence blocks and inline code first so we don't convert markdown inside them
  const fencePlaceholders: string[] = [];
  s0 = s0.replace(/```([\s\S]*?)```/g, (_m, p1: string) => {
    const idx = fencePlaceholders.push(p1) - 1;
    return `__CODEFENCE_${idx}__`;
  });

  const inlinePlaceholders: string[] = [];
  s0 = s0.replace(/`([^`]+?)`/g, (_m, p1: string) => {
    const idx = inlinePlaceholders.push(p1) - 1;
    return `__INLCODE_${idx}__`;
  });

  // 2) Extract Markdown links [text](url) into placeholders to avoid interfering with escaping/auto-linking
  const mdLinkPlaceholders: Array<{ text: string; url: string }> = [];
  s0 = s0.replace(/\[([^\]]+?)\]\(([^)\s]+)\)/g, (_m, text: string, url: string) => {
    const idx = mdLinkPlaceholders.push({ text, url }) - 1;
    return `__MDLINK_${idx}__`;
  });

  // 3) Escape remaining text safely
  let s = escapeHtml(s0);

  // 4) Convert bold **text** to <strong>
  s = s.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

  // 4.5) Convert italics *text* or _text_ to <em>, avoiding bold patterns
  // Use negative lookarounds to skip **bold** and __bold__
  s = s.replace(/(?<!\*)\*(?!\*)([^*]+?)\*(?!\*)/g, '<em>$1</em>');
  s = s.replace(/(?<!_)_(?!_)([^_]+?)_(?!_)/g, '<em>$1</em>');

  // 5) Convert markdown headings (# .. ######) into corresponding <h1>-<h6>
  // Keep a small visual style so headings remain compact inside chat bubbles
  s = s.replace(/^\s*(#{1,6})\s*(.+)$/gm, (_m, hashes: string, rest: string) => {
    const level = Math.min(6, hashes.length);
    return `<h${level} style="margin:0 0 .25rem 0; font-weight:700;">${rest}</h${level}>`;
  });

  // 6) Re-insert inline code placeholders as escaped <code>
  s = s.replace(/__INLCODE_(\d+)__/g, (_m, idx: string) => {
    const content = inlinePlaceholders[Number(idx)] || '';
    return `<code>${escapeHtml(content)}</code>`;
  });

  // 6.5) Convert remaining newlines to <br/> (outside code blocks)
  s = s.replace(/\n/g, '<br/>');

  // 7) Re-insert fence blocks as <pre><code>
  s = s.replace(/__CODEFENCE_(\d+)__/g, (_m, idx: string) => {
    const content = fencePlaceholders[Number(idx)] || '';
    return `<pre style="white-space:pre-wrap; overflow:auto; padding:8px; background:#f6f8fa; border-radius:6px;"><code>${escapeHtml(content)}</code></pre>`;
  });

  // 8) Auto-link bare URLs (http/https) remaining in escaped text
  // Avoid matching inside HTML tags by using a naive approach on text; acceptable for chat UI
  s = s.replace(/(https?:\/\/[^\s<]+[^\s<.)])/g, (m: string) => {
    const url = m;
    const safe = escapeHtml(url);
    return `<a href="${url}" target="_blank" rel="noopener noreferrer">${safe}</a>`;
  });

  // 9) Re-insert Markdown link placeholders as safe anchors
  s = s.replace(/__MDLINK_(\d+)__/g, (_m, idx: string) => {
    const entry = mdLinkPlaceholders[Number(idx)] || { text: '', url: '' };
    const txt = escapeHtml(entry.text || 'link');
    const url = String(entry.url || '').trim();
    const isHttp = /^https?:\/\//i.test(url);
    const href = isHttp ? url : '#';
    const extra = isHttp ? ' target="_blank" rel="noopener noreferrer"' : '';
    return `<a href="${href}"${extra}>${txt}</a>`;
  });

  return s;
}

// Clean and normalize LLM responses for display in chat.
export function cleanLLMText(raw: unknown): string {
  if (!raw && raw !== '') return '';
  let s = String(raw || '');
  // remove any think tags that might have remained
  s = s.replace(/<think>[\s\S]*?<\/think>/gi, '').trim();
  // remove code fence markers but keep inner content (we render fences separately)
  s = s.replace(/```/g, '');
  // convert list markers (-, +) at line start to bullet; keep '*' as it may denote bold/italic
  s = s.replace(/^\s*[-+]\s+/gm, '• ');
  // remove long dash/equal/underscore separators
  s = s.replace(/^[ _=-]{3,}\s*$/gm, '');
  // collapse multiple blank lines
  s = s.replace(/\n{3,}/g, '\n\n');
  return s.trim();
}
