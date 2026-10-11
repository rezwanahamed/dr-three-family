/* Optional export formatter. PostCSS is used only during migration. */
const fs = require('fs');
const path = require('path');
const postcss = require(require.resolve('postcss', {paths: [process.argv[2]]}));
const directory = path.resolve(__dirname, '../static/dental_family/css');
for (const name of fs.readdirSync(directory).filter(name => name.endsWith('.css'))) {
  const file = path.join(directory, name);
  const root = postcss.parse(fs.readFileSync(file, 'utf8'), {from: file});
  function format(container, depth) {
    container.raws.semicolon = true;
    container.raws.after = '\n' + '  '.repeat(Math.max(0, depth - 1));
    container.each(node => {
      node.raws.before = '\n' + '  '.repeat(depth);
      if (node.type === 'decl') node.raws.between = ': ';
      if (node.nodes) {
        node.raws.between = ' ';
        format(node, depth + 1);
      }
    });
  }
  format(root, 0);
  fs.writeFileSync(file, root.toString().trim() + '\n');
}
