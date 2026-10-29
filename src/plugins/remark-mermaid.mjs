/**
 * 把 ```mermaid 代码块转成 <div class="mermaid">，交给客户端 mermaid.js 渲染。
 * Shiki 会把 mermaid 识别成 plaintext，所以必须在 markdown 阶段拦截。
 */
export default function remarkMermaid() {
  console.log("[remark-mermaid] plugin created");
  return (tree) => {
    let hit = 0;
    const walk = (node) => {
      if (!node.children) return;
      for (let i = 0; i < node.children.length; i++) {
        const child = node.children[i];
        if (child.type === 'code' && (child.lang || '').toLowerCase() === 'mermaid') {
          hit++;
          node.children[i] = {
            type: 'html',
            value: `<div class="mermaid">${escapeHtml(child.value)}</div>`,
          };
        } else {
          walk(child);
        }
      }
    };
    walk(tree);
    if (hit) console.log(`[remark-mermaid] converted ${hit} diagram(s)`);
  };
}

function escapeHtml(s) {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}
