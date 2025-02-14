// app/api/image/route.ts
import { promises as fs } from 'fs';
import path from 'path';

export async function GET(request: Request) {
  // 請確認 imagePath 指向正確的圖片檔案
  const imagePath = "/Users/wei-chinwang/NTU/TSMC_hack/sn_17.jpg";

  const { searchParams } = new URL(request.url);
  const test_arg = searchParams.get('test_arg');
  console.log(test_arg);

  try {
    const data = await fs.readFile(imagePath);
    return new Response(data, {
      headers: { 'Content-Type': 'image/jpeg' },
    });
  } catch (err) {
    return new Response(JSON.stringify({ error: '讀取圖片失敗' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}
