import React from 'react';

function inline(text){
 return text.split(/(`[^`]+`|\[[^\]]+\]\([^\s)]+\))/g).map((part,index)=>{
  if(part.startsWith('`'))return <code key={index}>{part.slice(1,-1)}</code>;
  const match=part.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
  if(match){const safe=/^https?:\/\//i.test(match[2])||/^\/(?!\/)/.test(match[2]);return safe?<a key={index} href={match[2]} target={match[2].startsWith('/')?undefined:'_blank'} rel={match[2].startsWith('/')?undefined:'noopener noreferrer'}>{match[1]}</a>:<span key={index}>{match[1]}</span>;}
  return part;
 });
}
export function MarkdownView({text=''}){
 const sections=text.split(/```/);return <div className="personal-markdown">{sections.map((section,index)=>index%2?<pre key={index}><code>{section.replace(/^[\w+-]*\n/,'')}</code></pre>:<div key={index}>{section.split('\n').map((line,row)=>{
  const heading=line.match(/^(#{1,4})\s+(.*)/);if(heading){const Tag='h'+Math.min(heading[1].length+1,5);return <Tag key={row}>{inline(heading[2])}</Tag>;}
  if(/^[-*]\s/.test(line))return <p className="personal-markdown-bullet" key={row}>• {inline(line.slice(2))}</p>;
  if(line.startsWith('> '))return <blockquote key={row}>{inline(line.slice(2))}</blockquote>;
  return line?<p key={row}>{inline(line)}</p>:<div className="personal-markdown-space" key={row}/>;
 })}</div>)}</div>;
}
