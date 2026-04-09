export default function NextImage({ src, alt, width, height, className, fill, ...props }) {
  const style = fill ? { width: '100%', height: '100%', objectFit: 'cover' } : {};
  return <img src={src} alt={alt} width={width} height={height} className={className} style={style} {...props} />;
}
