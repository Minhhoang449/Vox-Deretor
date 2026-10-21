"""Compile the local playlist catalog into one self-contained Codex Canvas."""
import json
import os
import sys

from channels import load_channels
from playlists import load_catalog


def run(path):
    catalog = load_catalog()
    roster = {channel['id']: channel for channel in load_channels()}
    data = [{'id': group['channel_id'], 'name': roster[group['channel_id']]['display_name'],
             'language': roster[group['channel_id']]['language'],
             'playlists': [{key: entry[key] for key in ('id', 'title', 'description', 'label_vi', 'kind', 'include_when')}
                           for entry in group['playlists']]}
            for group in catalog['channels']]
    source = '''import { useState, useHostTheme, Button, Select, Stack, Row, H1, H2, Text, Card, CardBody } from "cursor/canvas";

type Playlist = { id: string; title: string; description: string; label_vi: string; kind: string; include_when: string; };
type Channel = { id: string; name: string; language: string; playlists: Playlist[]; };
const DATA: Channel[] = __DATA__;

export default function PlaylistCatalog() {
  const theme = useHostTheme();
  const [channelId, setChannelId] = useState("moc-vy");
  const [playlistId, setPlaylistId] = useState("moc-vy-doi-song");
  const [copied, setCopied] = useState("");
  const channel = DATA.find(item => item.id === channelId)!;
  const chosen = channel.playlists.find(item => item.id === playlistId) || channel.playlists[0];
  const example = JSON.stringify({ youtube_metadata: { playlists: { primary_id: chosen.id } } }, null, 2);
  async function copy(value: string, label: string) {
    try {
      if (navigator.clipboard?.writeText) await navigator.clipboard.writeText(value);
      else {
        const field = document.createElement("textarea"); field.value = value;
        document.body.appendChild(field); field.select();
        const ok = document.execCommand("copy"); field.remove();
        if (!ok) throw new Error("clipboard unavailable");
      }
      setCopied("Đã sao chép " + label);
    } catch { setCopied("Có thể chọn nội dung bên dưới và sao chép bằng bàn phím."); }
  }
  return <div style={{padding:24, color:theme.text.primary, background:theme.bg.editor, fontSize:14, lineHeight:1.65}}>
    <Stack gap={14}>
      <H1>Danh sách phát cho các câu chuyện nhiệm vụ</H1>
      <Text>{DATA.reduce((total,item)=>total+item.playlists.length,0)} playlist · {new Set(DATA.map(item=>item.language)).size} ngôn ngữ · Cập nhật __UPDATED_ON__</Text>
      <div style={{color:theme.text.secondary}}>Chọn kênh và nhóm nội dung để sao chép tên, mô tả vào YouTube Studio. Mỗi kênh có bốn nhóm nhiệm vụ và một nhánh can thiệp chiến tranh/xung đột. ID nội bộ giữ ổn định cho các tập đã có.</div>
      <Row gap={12}>
        <Select value={channelId} options={DATA.map(item => ({value:item.id, label:item.name + " · " + item.language.toUpperCase()}))}
          onChange={value => {setChannelId(value); setPlaylistId(DATA.find(item => item.id===value)!.playlists[0].id); setCopied("");}} />
        <Text>{channel.playlists.length} nhóm nội dung</Text>
      </Row>
      <div style={{display:"flex", gap:24, flexWrap:"wrap", alignItems:"flex-start"}}>
        <div style={{flex:"1 1 240px", minWidth:0}}>
          <H2>{channel.name}</H2>
          {channel.playlists.map((playlist, index) => <div key={playlist.id} style={{padding:"12px 0", borderBottom:"1px solid " + theme.stroke.primary}}>
            <Button variant={playlist.id===chosen.id?"primary":"ghost"} onClick={() => {setPlaylistId(playlist.id); setCopied("");}}>
              {index+1}. {playlist.label_vi}
            </Button>
            <div style={{color:theme.text.tertiary, marginTop:6}}>{playlist.kind==="core"?"Nhóm nội dung chính":"Nhánh chuyên đề: chọn khi nội dung phù hợp"}</div>
          </div>)}
          <p style={{color:theme.text.secondary}}>Ưu tiên mở playlist khi đã có video phù hợp. Tên và mô tả là đề xuất biên tập, chưa đo lượng tìm kiếm hay hiệu quả xếp hạng.</p>
        </div>
        <div style={{flex:"2 1 380px", minWidth:0}}>
          <Card><CardBody><Stack gap={12}>
            <H2>{chosen.title}</H2>
            <div style={{color:theme.text.secondary}}>Tên công khai · {chosen.title.length} ký tự · Ngôn ngữ {channel.language.toUpperCase()}</div>
            <Row gap={8}><Button onClick={() => {void copy(chosen.title,"tiêu đề");}}>Sao chép tiêu đề</Button><Button onClick={() => {void copy(chosen.description,"mô tả");}}>Sao chép mô tả</Button></Row>
            <p lang={channel.language} style={{margin:0, whiteSpace:"pre-wrap", fontSize:15, lineHeight:1.75}}>{chosen.description}</p>
            <div style={{color:theme.text.tertiary}}>Mô tả công khai · {chosen.description.length} ký tự</div>
          </Stack></CardBody></Card>
          <div style={{marginTop:20}}>
            <H2>Khai báo khi xuất metadata</H2>
            <p style={{color:theme.text.secondary}}>Đoạn JSON minh họa nhóm đang xem; chọn theo câu chuyện thực tế của tập. Có thể thêm tối đa hai ID vào additional_ids và ghi selection_reason. ID nội bộ khác với ID playlist trên YouTube.</p>
            <pre style={{background:theme.fill.tertiary, borderRadius:6, padding:14, overflowX:"auto", color:theme.text.primary, fontSize:12}}>{example}</pre>
            <Button onClick={() => {void copy(example,"JSON playlist");}}>Sao chép JSON playlist</Button>
            <p style={{color:theme.text.secondary}}>Bộ xuất ghi playlist chính, bổ sung và mô tả vào youtube-upload.txt; đồng thời tạo youtube-playlists.txt và youtube-playlists.json. Gợi ý chưa chọn luôn mang trạng thái pending_selection.</p>
          </div>
        </div>
      </div>
      {copied && <div role="status" style={{color:theme.accent.primary}}>{copied}</div>}
      <div style={{borderTop:"1px solid "+theme.stroke.primary, paddingTop:12, color:theme.text.tertiary, fontSize:12}}>
        Nguồn nội dung: config/playlists.json · Hướng dẫn: <a style={{color:theme.text.link}} href="https://support.google.com/youtube/answer/16090438">YouTube Search</a>, <a style={{color:theme.text.link}} href="https://support.google.com/youtube/answer/6083634">Quản lý playlist</a>. Bộ đề xuất này chưa được đối chiếu với các playlist trên tài khoản YouTube.
      </div>
    </Stack>
  </div>;
}
'''.replace('__DATA__', json.dumps(data, ensure_ascii=False, indent=2)).replace('__UPDATED_ON__', catalog['updated_on'])
    # The caller controls the approved output directory; the managed Canvas
    # directory is already provisioned and must not be created here.
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(source)
    print(os.path.abspath(path))


if __name__ == '__main__':
    if len(sys.argv)!=2:
        raise SystemExit('usage: python scripts/export_playlist_canvas.py <output.tsx>')
    run(sys.argv[1])
