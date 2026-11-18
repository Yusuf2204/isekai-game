const tsJest = require('ts-jest').default;
const transformer = tsJest.createTransformer({
  tsconfig: {
    jsx: 'react-jsx',
    esModuleInterop: true,
  },
});

module.exports = {
  process(sourceText, sourcePath, options) {
    const transformedText = sourceText.replace(/import\.meta\.env/g, 'process.env');
    return transformer.process(transformedText, sourcePath, options);
  },
};
