import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const source = await readFile(new URL('../crm_v2/photo_assets/viewer.js', import.meta.url), 'utf8');
const {normalize, safePart, childDirectory, validateRoot, houseImages, cloudURL} =
  await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
const directory = (name, children=[]) => ({name, kind:'directory', async *entries() {for(const c of children) yield [c.name,c];}});
test('address names ignore accents/case; ambiguous matches are rejected', async () => {
  assert.equal(normalize(' PHÚ NHUẬN '), 'phu nhuan');
  assert.equal(normalize('Đặng Văn Ngữ'), 'dang van ngu');
  await assert.rejects(childDirectory(directory('x',[directory('Phú Nhuận'),directory('Phu Nhuan')]), 'Phu Nhuan'));
  for (const x of ['..','a/b','a\\b','']) assert.throws(()=>safePart(x));
});
test('validate SH Total, exact house, JPG only, natural ordering', async () => {
  const root=directory('SH Total',[
    directory('Bình Thạnh'), directory('Phu Nhuan', [directory('Dang Van Ngu',[
      directory('123 Dang Van Ngu', [{name:'10.jpg',kind:'file'},{name:'2.JPG',kind:'file'},
        {name:'old.png',kind:'file'}, directory('SF',[{name:'map.jpg',kind:'file'}])])])])]);
  assert.equal(await validateRoot(root),root);
  const images=await houseImages(root,{district:'Phú Nhuận',street:'Đặng Văn Ngữ',number:'123'});
  assert.deepEqual(images.map(f=>f.name),['2.JPG','10.jpg']);
  await assert.rejects(houseImages(root,{district:'Phú Nhuận',street:'Đặng Văn Ngữ',number:'999'}));
  await assert.rejects(validateRoot(directory('SH Total',[directory('Binh Thanh')])));
  await assert.rejects(validateRoot(directory('wrong')));
});
test('cloud fallback allows HTTPS and rejects unsafe schemes', () => {
  assert.equal(cloudURL('javascript:alert(1)'), '');
  assert.equal(cloudURL('http://drive.google.com/a'), '');
  assert.equal(cloudURL('https://drive.google.com/a'), 'https://drive.google.com/a');
});
