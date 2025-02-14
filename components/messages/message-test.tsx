import React, { useEffect, useState } from "react"

const TestImage = () => {
  //   const [imgUrl, setImgUrl] = useState<string>('')

  //   useEffect(() => {
  //     fetch('/api/image')
  //       .then(response => response.blob())
  //       .then(blob => {
  //         const url = URL.createObjectURL(blob)
  //         setImgUrl(url)
  //       })
  //       .catch(error => console.error('Fetch image error:', error))
  //   }, [])

  return (
    <div>
      <img
        src="/api/image?test_arg=6889"
        alt="test image"
        height="100px"
        width="100px"
      />
    </div>
  )
}

export { TestImage }
