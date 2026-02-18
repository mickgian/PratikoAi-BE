// Mock for remark-gfm ESM module
// This module uses ESM syntax which Jest can't parse by default
module.exports = function remarkGfm() {
  return function (tree) {
    return tree;
  };
};
