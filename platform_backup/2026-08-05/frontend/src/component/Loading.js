import React, { useEffect, useState } from 'react';
import Swal from 'sweetalert2';
import withReactContent from 'sweetalert2-react-content';

const MySwal = withReactContent(Swal);

const Loading = ({ show }) => {
    const [timer, setTimer] = useState(0);

    useEffect(() => {
        let interval;

        if (show) {
            MySwal.fire({
                title: 'Loading...',
                html: `Please wait. Elapsed time: <b id="timer">${timer}</b> seconds.`,
                allowOutsideClick: false,
                didOpen: () => {
                    Swal.showLoading();
                    interval = setInterval(() => {
                        setTimer((prevTimer) => {
                            const newTimer = prevTimer + 1;
                            // 更新 SweetAlert2 的內容
                            Swal.update({
                                html: `Please wait. Elapsed time: <b>${newTimer}</b> seconds.`
                            });
                            return newTimer;
                        });
                    }, 1000);
                }
            });
        } else {
            Swal.close();
            clearInterval(interval);
        }

        return () => {
            clearInterval(interval);
            Swal.close(); 
        };
    }, [show]);

    return null;
};

export default Loading;
