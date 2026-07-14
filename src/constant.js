import { createContext } from "react"

const dev = {
    rootApiIP : "http://140.116.214.140:8217/ncku_hospital",
    rootPathPrefix : "/variant"
}

// const prod = {
//     rootApiIP : "https://cosbi10.ee.ncku.edu.tw/ncku_hospital",
//     rootPathPrefix : "/variant"
// }
// const dev = {
//     rootApiIP : "/ncku_hospital",
//     rootPathPrefix : "/variant"
// }
const prod = {
    rootApiIP : "/ncku_hospital",
    rootPathPrefix : "/variant"
}

export const config = process.env.NODE_ENV === "development" ? dev : prod
